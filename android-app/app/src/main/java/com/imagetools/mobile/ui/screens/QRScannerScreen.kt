package com.imagetools.mobile.ui.screens

import android.Manifest
import android.util.Log
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.google.gson.Gson
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import com.imagetools.mobile.data.models.QRCodeData
import com.imagetools.mobile.data.models.ValidateSecretRequest
import com.imagetools.mobile.data.network.RetrofitClient
import com.imagetools.mobile.utils.PairingPreferences
import kotlinx.coroutines.launch
import java.util.concurrent.Executors

private const val TAG = "QRScannerScreen"

@Composable
fun QRScannerScreen(
    pairingPrefs: PairingPreferences,
    onPaired: () -> Unit,
    onCancel: () -> Unit
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val scope = rememberCoroutineScope()
    
    var hasCameraPermission by remember { mutableStateOf(false) }
    var isProcessing by remember { mutableStateOf(false) }
    
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        hasCameraPermission = isGranted
        if (!isGranted) {
            Toast.makeText(context, "Camera permission required", Toast.LENGTH_SHORT).show()
            onCancel()
        }
    }
    
    LaunchedEffect(Unit) {
        permissionLauncher.launch(Manifest.permission.CAMERA)
    }
    
    if (hasCameraPermission) {
        Box(modifier = Modifier.fillMaxSize()) {
            AndroidView(
                factory = { ctx ->
                    val previewView = PreviewView(ctx)
                    val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)
                    
                    cameraProviderFuture.addListener({
                        Log.d(TAG, "Camera provider ready, initializing camera...")
                        val cameraProvider = cameraProviderFuture.get()
                        val preview = Preview.Builder().build()
                        preview.setSurfaceProvider(previewView.surfaceProvider)
                        
                        val imageAnalyzer = ImageAnalysis.Builder()
                            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                            .build()
                        
                        val barcodeScanner = BarcodeScanning.getClient()
                        val executor = Executors.newSingleThreadExecutor()
                        
                        Log.d(TAG, "Setting up barcode analyzer...")
                        
                        imageAnalyzer.setAnalyzer(executor) { imageProxy ->
                            if (!isProcessing) {
                                val mediaImage = imageProxy.image
                                if (mediaImage != null) {
                                    val image = InputImage.fromMediaImage(
                                        mediaImage,
                                        imageProxy.imageInfo.rotationDegrees
                                    )
                                    
                                    barcodeScanner.process(image)
                                        .addOnSuccessListener { barcodes ->
                                            if (barcodes.isNotEmpty() && !isProcessing) {
                                                Log.d(TAG, "Detected ${barcodes.size} barcode(s)")
                                                for (barcode in barcodes) {
                                                    barcode.rawValue?.let { qrData ->
                                                        Log.d(TAG, "QR Code data: ${qrData.take(100)}...")
                                                        isProcessing = true
                                                        scope.launch {
                                                            handleQRCode(
                                                                qrData = qrData,
                                                                pairingPrefs = pairingPrefs,
                                                                context = context,
                                                                onPaired = onPaired,
                                                                onError = { 
                                                                    isProcessing = false
                                                                    Log.d(TAG, "Reset isProcessing flag after error")
                                                                }
                                                            )
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                        .addOnFailureListener { e ->
                                            Log.e(TAG, "Barcode scanning failed", e)
                                        }
                                        .addOnCompleteListener {
                                            imageProxy.close()
                                        }
                                } else {
                                    imageProxy.close()
                                }
                            } else {
                                imageProxy.close()
                            }
                        }
                        
                        val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
                        
                        try {
                            cameraProvider.unbindAll()
                            cameraProvider.bindToLifecycle(
                                lifecycleOwner,
                                cameraSelector,
                                preview,
                                imageAnalyzer
                            )
                            Log.d(TAG, "Camera bound successfully, scanner is active")
                            Toast.makeText(ctx, "Scanner ready", Toast.LENGTH_SHORT).show()
                        } catch (e: Exception) {
                            Log.e(TAG, "Camera binding failed", e)
                            Toast.makeText(ctx, "Camera error: ${e.message}", Toast.LENGTH_LONG).show()
                        }
                    }, ContextCompat.getMainExecutor(ctx))
                    
                    previewView
                },
                modifier = Modifier.fillMaxSize()
            )
            
            // Overlay
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(24.dp),
                verticalArrangement = Arrangement.SpaceBetween
            ) {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.9f)
                    )
                ) {
                    Text(
                        text = "Scan the QR code from Image Tools",
                        modifier = Modifier.padding(16.dp),
                        style = MaterialTheme.typography.bodyLarge
                    )
                }
                
                Button(
                    onClick = onCancel,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Cancel")
                }
            }
            
            if (isProcessing) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator()
                }
            }
        }
    }
}

private suspend fun handleQRCode(
    qrData: String,
    pairingPrefs: PairingPreferences,
    context: android.content.Context,
    onPaired: () -> Unit,
    onError: () -> Unit
) {
    try {
        Log.d(TAG, "Parsing QR code data...")
        val gson = Gson()
        val qrCodeData = gson.fromJson(qrData, QRCodeData::class.java)
        
        Log.d(TAG, "QR data parsed: instanceUrl=${qrCodeData.instanceUrl}, pairingId=${qrCodeData.pairingId}")
        
        // Set base URL
        RetrofitClient.setBaseUrl(qrCodeData.instanceUrl)
        
        Log.d(TAG, "Validating secret with backend...")
        // Validate secret
        val validateRequest = ValidateSecretRequest(qrCodeData.sharedSecret)
        val response = RetrofitClient.getApi().validateSecret(validateRequest)
        
        Log.d(TAG, "Validation response: ${response.code()}, success: ${response.isSuccessful}")
        
        if (response.isSuccessful && response.body()?.valid == true) {
            val body = response.body()!!
            val deviceName = body.deviceName ?: "Android Device"
            
            Log.d(TAG, "Pairing validated! Saving to preferences...")
            
            // Save pairing with long-term authorization secrets
            pairingPrefs.savePairing(
                instanceUrl = qrCodeData.instanceUrl,
                sharedSecret = qrCodeData.sharedSecret,
                pairingId = body.pairingId ?: qrCodeData.pairingId,
                sessionId = body.sessionId ?: qrCodeData.sessionId,
                deviceName = deviceName,
                longTermSecret = body.longTermSecret ?: "",
                refreshSecret = body.refreshSecret ?: "",
                longTermExpiresAt = body.longTermExpiresAt ?: "",
                refreshExpiresAt = body.refreshExpiresAt ?: ""
            )
            
            Toast.makeText(context, "Paired successfully!", Toast.LENGTH_SHORT).show()
            onPaired()
        } else {
            val errorBody = response.errorBody()?.string()
            Log.e(TAG, "Invalid QR code: ${response.code()} - $errorBody")
            Toast.makeText(context, "Invalid QR code: ${response.code()}", Toast.LENGTH_LONG).show()
            onError()
        }
    } catch (e: Exception) {
        Log.e(TAG, "Error processing QR code", e)
        Toast.makeText(context, "Error: ${e.message}", Toast.LENGTH_LONG).show()
        onError()
    }
}
