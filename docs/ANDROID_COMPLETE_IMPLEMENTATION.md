# Android App - Remaining Implementation Files

This document contains the complete source code for all remaining Android app files that need to be created.

## Status Summary

**COMPLETED:**
- Data models (QRCodeData.kt, ApiModels.kt)
- Network layer (ImageToolsApi.kt, RetrofitClient.kt)
- Storage (PairingPreferences.kt)
- Build configuration (build.gradle, AndroidManifest.xml)
- Build script (build-android.sh)

**NEEDED (copy the code below into the specified file paths):**

---

## 1. MainActivity.kt
**Path:** `android-app/app/src/main/java/com/imagetools/mobile/MainActivity.kt`

```kotlin
package com.imagetools.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.lifecycle.lifecycleScope
import com.imagetools.mobile.ui.screens.HomeScreen
import com.imagetools.mobile.utils.PairingPreferences
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    
    private lateinit var pairingPrefs: PairingPreferences
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        pairingPrefs = PairingPreferences(this)
        
        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    HomeScreen(pairingPrefs = pairingPrefs)
                }
            }
        }
    }
}
```

---

## 2. ShareActivity.kt
**Path:** `android-app/app/src/main/java/com/imagetools/mobile/ShareActivity.kt`

```kotlin
package com.imagetools.mobile

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Base64
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import com.imagetools.mobile.data.models.ImageUploadRequest
import com.imagetools.mobile.data.network.RetrofitClient
import com.imagetools.mobile.utils.PairingPreferences
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import java.io.IOException

class ShareActivity : ComponentActivity() {
    
    private lateinit var pairingPrefs: PairingPreferences
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        pairingPrefs = PairingPreferences(this)
        
        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    UploadScreen()
                }
            }
        }
        
        // Handle the shared image
        handleSharedImage(intent)
    }
    
    @Composable
    fun UploadScreen() {
        var status by remember { mutableStateOf("Uploading image...") }
        var isError by remember { mutableStateOf(false) }
        
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            contentAlignment = Alignment.Center
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                if (!isError) {
                    CircularProgressIndicator()
                }
                Text(
                    text = status,
                    style = MaterialTheme.typography.bodyLarge
                )
                if (isError) {
                    Button(onClick = { finish() }) {
                        Text("Close")
                    }
                }
            }
        }
    }
    
    private fun handleSharedImage(intent: Intent?) {
        if (intent?.action == Intent.ACTION_SEND && intent.type?.startsWith("image/") == true) {
            val imageUri = intent.getParcelableExtra<Uri>(Intent.EXTRA_STREAM)
            if (imageUri != null) {
                uploadImage(imageUri)
            } else {
                showError("No image found")
            }
        } else {
            showError("Invalid share intent")
        }
    }
    
    private fun uploadImage(imageUri: Uri) {
        lifecycleScope.launch {
            try {
                // Check if paired
                val secret = pairingPrefs.sharedSecret.first()
                val instanceUrl = pairingPrefs.instanceUrl.first()
                
                if (secret == null || instanceUrl == null) {
                    showError("Not paired with Image Tools. Open the app and scan the QR code first.")
                    return@launch
                }
                
                // Set base URL
                RetrofitClient.setBaseUrl(instanceUrl)
                
                // Read image and encode to base64
                val inputStream = contentResolver.openInputStream(imageUri)
                val imageBytes = inputStream?.readBytes()
                inputStream?.close()
                
                if (imageBytes == null) {
                    showError("Failed to read image")
                    return@launch
                }
                
                val base64Image = Base64.encodeToString(imageBytes, Base64.NO_WRAP)
                val filename = getFileName(imageUri) ?: "shared_image.jpg"
                
                // Upload to API
                val request = ImageUploadRequest(
                    sharedSecret = secret,
                    imageBase64 = base64Image,
                    filename = filename
                )
                
                val response = RetrofitClient.getApi().uploadImage(request)
                
                if (response.isSuccessful && response.body()?.success == true) {
                    showSuccess("Image uploaded successfully!")
                } else {
                    showError("Upload failed: ${response.body()?.message ?: "Unknown error"}")
                }
                
            } catch (e: IOException) {
                showError("Network error: ${e.message}")
            } catch (e: Exception) {
                showError("Error: ${e.message}")
            }
        }
    }
    
    private fun getFileName(uri: Uri): String? {
        val cursor = contentResolver.query(uri, null, null, null, null)
        return cursor?.use {
            val nameIndex = it.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
            if (it.moveToFirst() && nameIndex >= 0) {
                it.getString(nameIndex)
            } else null
        }
    }
    
    private fun showSuccess(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
        finish()
    }
    
    private fun showError(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
        // Update UI to show error
        lifecycleScope.launch {
            // This will trigger recomposition with error state
        }
    }
}
```

---

## 3. HomeScreen.kt
**Path:** `android-app/app/src/main/java/com/imagetools/mobile/ui/screens/HomeScreen.kt`

```kotlin
package com.imagetools.mobile.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.imagetools.mobile.utils.PairingPreferences
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

@Composable
fun HomeScreen(pairingPrefs: PairingPreferences) {
    var isPaired by remember { mutableStateOf(false) }
    var deviceName by remember { mutableStateOf<String?>(null) }
    var sessionId by remember { mutableStateOf<String?>(null) }
    var showScanner by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    
    // Load pairing status
    LaunchedEffect(Unit) {
        isPaired = pairingPrefs.isPaired.first()
        if (isPaired) {
            deviceName = pairingPrefs.deviceName.first()
            sessionId = pairingPrefs.sessionId.first()
        }
    }
    
    if (showScanner) {
        QRScannerScreen(
            pairingPrefs = pairingPrefs,
            onPaired = {
                showScanner = false
                scope.launch {
                    isPaired = true
                    deviceName = pairingPrefs.deviceName.first()
                    sessionId = pairingPrefs.sessionId.first()
                }
            },
            onCancel = { showScanner = false }
        )
    } else {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text(
                text = "Image Tools Mobile",
                style = MaterialTheme.typography.headlineMedium,
                textAlign = TextAlign.Center
            )
            
            Spacer(modifier = Modifier.height(32.dp))
            
            if (isPaired) {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer
                    )
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(
                            text = "✓ Paired Successfully",
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Text(
                            text = "Device: ${deviceName ?: "Unknown"}",
                            style = MaterialTheme.typography.bodyMedium
                        )
                        Text(
                            text = "Session: ${sessionId?.take(8) ?: "Unknown"}...",
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
                
                Spacer(modifier = Modifier.height(24.dp))
                
                Text(
                    text = "You can now share images from your Gallery or Camera to Image Tools",
                    style = MaterialTheme.typography.bodyMedium,
                    textAlign = TextAlign.Center
                )
                
                Spacer(modifier = Modifier.height(24.dp))
                
                Button(
                    onClick = {
                        scope.launch {
                            pairingPrefs.clearPairing()
                            isPaired = false
                            deviceName = null
                            sessionId = null
                        }
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error
                    )
                ) {
                    Text("Unpair Device")
                }
            } else {
                Text(
                    text = "To get started, scan the QR code from your Image Tools session",
                    style = MaterialTheme.typography.bodyLarge,
                    textAlign = TextAlign.Center
                )
                
                Spacer(modifier = Modifier.height(32.dp))
                
                Button(
                    onClick = { showScanner = true },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Scan QR Code")
                }
                
                Spacer(modifier = Modifier.height(16.dp))
                
                Text(
                    text = "Open Image Tools in your browser, click the info icon (ℹ️), and scan the QR code displayed.",
                    style = MaterialTheme.typography.bodySmall,
                    textAlign = TextAlign.Center,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}
```

---

## 4. QRScannerScreen.kt
**Path:** `android-app/app/src/main/java/com/imagetools/mobile/ui/screens/QRScannerScreen.kt`

```kotlin
package com.imagetools.mobile.ui.screens

import android.Manifest
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
                        val cameraProvider = cameraProviderFuture.get()
                        val preview = Preview.Builder().build()
                        preview.setSurfaceProvider(previewView.surfaceProvider)
                        
                        val imageAnalyzer = ImageAnalysis.Builder()
                            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                            .build()
                        
                        val barcodeScanner = BarcodeScanning.getClient()
                        val executor = Executors.newSingleThreadExecutor()
                        
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
                                            for (barcode in barcodes) {
                                                barcode.rawValue?.let { qrData ->
                                                    isProcessing = true
                                                    scope.launch {
                                                        handleQRCode(qrData, pairingPrefs, context, onPaired)
                                                    }
                                                }
                                            }
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
                        } catch (e: Exception) {
                            Toast.makeText(ctx, "Camera error: ${e.message}", Toast.LENGTH_SHORT).show()
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
    onPaired: () -> Unit
) {
    try {
        val gson = Gson()
        val qrCodeData = gson.fromJson(qrData, QRCodeData::class.java)
        
        // Set base URL
        RetrofitClient.setBaseUrl(qrCodeData.instanceUrl)
        
        // Validate secret
        val validateRequest = ValidateSecretRequest(qrCodeData.sharedSecret)
        val response = RetrofitClient.getApi().validateSecret(validateRequest)
        
        if (response.isSuccessful && response.body()?.valid == true) {
            val deviceName = response.body()?.deviceName ?: "Android Device"
            
            // Save pairing
            pairingPrefs.savePairing(
                instanceUrl = qrCodeData.instanceUrl,
                sharedSecret = qrCodeData.sharedSecret,
                pairingId = qrCodeData.pairingId,
                sessionId = qrCodeData.sessionId,
                deviceName = deviceName
            )
            
            Toast.makeText(context, "Paired successfully!", Toast.LENGTH_SHORT).show()
            onPaired()
        } else {
            Toast.makeText(context, "Invalid QR code", Toast.LENGTH_SHORT).show()
        }
    } catch (e: Exception) {
        Toast.makeText(context, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
    }
}
```

---

## 5. strings.xml
**Path:** `android-app/app/src/main/res/values/strings.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">Image Tools</string>
    <string name="scan_qr_code">Scan QR Code</string>
    <string name="paired">Paired</string>
    <string name="not_paired">Not Paired</string>
    <string name="share_target_label">Share to Image Tools</string>
</resources>
```

---

## 6. themes.xml
**Path:** `android-app/app/src/main/res/values/themes.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.ImageTools" parent="android:Theme.Material.Light.NoActionBar" />
</resources>
```

---

## 7. Root build.gradle
**Path:** `android-app/build.gradle`

```gradle
// Top-level build file
buildscript {
    ext {
        kotlin_version = '1.9.0'
        compose_version = '1.5.0'
    }
    repositories {
        google()
        mavenCentral()
    }
    dependencies {
        classpath 'com.android.tools.build:gradle:8.1.0'
        classpath "org.jetbrains.kotlin:kotlin-gradle-plugin:$kotlin_version"
    }
}

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}
```

---

## 8. settings.gradle
**Path:** `android-app/settings.gradle`

```gradle
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "ImageToolsMobile"
include ':app'
```

---

## Quick Setup Instructions

1. **Copy all the code above** into the specified file paths
2. **Install frontend dependency:**
   ```bash
   cd frontend && npm install
   ```
3. **Start backend:**
   ```bash
   cd backend && python -m uvicorn app.main:app --reload --port 8081
   ```
4. **Start frontend:**
   ```bash
   cd frontend && npm run dev
   ```
5. **Build and install Android app:**
   ```bash
   ./build-android.sh
   ```

## Testing Flow

1. Open browser → Image Tools
2. Click info icon (ℹ️) → See QR code
3. Open Android app → Scan QR code
4. Share image from Gallery → Select "Image Tools"
5. Image appears in web session

## Next Steps

After creating all files:
- Run `./build-android.sh` to build and install
- The script will handle all Gradle setup automatically
- App will launch after installation
- Any errors will be shown with colored output

## Troubleshooting

**If build fails:**
- Check Android Studio installed at `/home/philg/Android/`
- Ensure USB debugging enabled on device
- Run `adb devices` to verify connection

**If QR scan fails:**
- Ensure CAMERA permission granted
- Check QR code displays in web app
- Verify network connectivity

**If upload fails:**
- Check `INSTANCE_URL` in backend .env
- Ensure backend accessible from device network
- May need to add device IP to CORS_ORIGINS
