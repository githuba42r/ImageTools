package com.imagetools.mobile.ui.screens

import android.os.Build
import android.util.Log
import android.widget.Toast
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.imagetools.mobile.R
import com.imagetools.mobile.BuildConfig
import com.imagetools.mobile.data.models.ValidateAuthRequest
import com.imagetools.mobile.data.models.ValidateSecretRequest
import com.imagetools.mobile.data.network.RetrofitClient
import com.imagetools.mobile.utils.PairingPreferences
import com.imagetools.mobile.utils.DeviceInfo
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

private const val TAG = "HomeScreen"

@Composable
fun HomeScreen(
    pairingPrefs: PairingPreferences,
    pendingPairingData: Map<String, String>? = null
) {
    val context = LocalContext.current
    var isPaired by remember { mutableStateOf(false) }
    var deviceName by remember { mutableStateOf<String?>(null) }
    var sessionId by remember { mutableStateOf<String?>(null) }
    var showScanner by remember { mutableStateOf(false) }
    var showUnpairDialog by remember { mutableStateOf(false) }
    var isProcessingIntent by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    
    // Handle pending pairing data from intent
    LaunchedEffect(pendingPairingData) {
        if (pendingPairingData != null && !isProcessingIntent) {
            isProcessingIntent = true
            Log.d(TAG, "Processing pending pairing data from intent (isPaired=$isPaired)")
            
            try {
                val url = pendingPairingData["url"]!!
                val secret = pendingPairingData["secret"]!!
                val pairingId = pendingPairingData["pairing_id"]!!
                val sessionIdValue = pendingPairingData["session_id"]!!
                
                Log.d(TAG, "Pairing parameters: url=$url, pairingId=$pairingId, sessionId=$sessionIdValue")
                
                // Set base URL
                RetrofitClient.setBaseUrl(url)
                
                Log.d(TAG, "Validating secret with backend...")
                // Validate secret with device information
                val validateRequest = ValidateSecretRequest(
                    sharedSecret = secret,
                    deviceModel = "${Build.MANUFACTURER} ${Build.MODEL}",
                    deviceManufacturer = Build.MANUFACTURER,
                    deviceOwner = DeviceInfo.getDeviceOwner(context),
                    osVersion = "Android ${Build.VERSION.RELEASE}",
                    appVersion = BuildConfig.VERSION_NAME
                )
                val response = RetrofitClient.getApi().validateSecret(validateRequest)
                
                Log.d(TAG, "Validation response: ${response.code()}, success: ${response.isSuccessful}")
                
                if (response.isSuccessful && response.body()?.valid == true) {
                    val body = response.body()!!
                    val deviceNameValue = body.deviceName ?: "Android Device"
                    
                    Log.d(TAG, "Pairing validated! Saving to preferences...")
                    
                    // Save pairing with long-term authorization secrets
                    pairingPrefs.savePairing(
                        instanceUrl = url,
                        sharedSecret = secret,
                        pairingId = body.pairingId ?: pairingId,
                        sessionId = body.sessionId ?: sessionIdValue,
                        deviceName = deviceNameValue,
                        longTermSecret = body.longTermSecret ?: "",
                        refreshSecret = body.refreshSecret ?: "",
                        longTermExpiresAt = body.longTermExpiresAt ?: "",
                        refreshExpiresAt = body.refreshExpiresAt ?: ""
                    )
                    
                    isPaired = true
                    deviceName = deviceNameValue
                    sessionId = body.sessionId ?: sessionIdValue
                    
                    Log.d(TAG, "Pairing complete!")
                    Toast.makeText(context, "Paired successfully via link!", Toast.LENGTH_SHORT).show()
                } else {
                    val errorBody = response.errorBody()?.string()
                    Log.e(TAG, "Invalid pairing: ${response.code()} - $errorBody")
                    Toast.makeText(context, "Invalid pairing link: ${response.code()}", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error processing pairing intent", e)
                Toast.makeText(context, "Error: ${e.message}", Toast.LENGTH_LONG).show()
            } finally {
                isProcessingIntent = false
            }
        }
    }
    
    LaunchedEffect(Unit) {
        isPaired = pairingPrefs.isPaired.first()
        if (isPaired) {
            deviceName = pairingPrefs.deviceName.first()
            sessionId = pairingPrefs.sessionId.first()
        }
    }
    
    // Unpair confirmation dialog
    if (showUnpairDialog) {
        AlertDialog(
            onDismissRequest = { showUnpairDialog = false },
            title = { Text("Unpair Device?") },
            text = {
                Text(
                    "Are you sure you want to unpair this device?\n\n" +
                    "You will need to scan the QR code again to share images."
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        scope.launch {
                            // Call unpair endpoint before clearing local data
                            try {
                                val longTermSecret = pairingPrefs.longTermSecret.first()
                                if (!longTermSecret.isNullOrEmpty()) {
                                    Log.d(TAG, "Calling unpair endpoint...")
                                    val response = RetrofitClient.getApi().unpairDevice(
                                        ValidateAuthRequest(longTermSecret = longTermSecret)
                                    )
                                    if (response.isSuccessful) {
                                        Log.d(TAG, "Unpaired from server successfully")
                                        Toast.makeText(context, "Device unpaired successfully", Toast.LENGTH_SHORT).show()
                                    } else {
                                        Log.w(TAG, "Failed to unpair from server: ${response.code()}")
                                        // Continue with local unpair even if server call fails
                                    }
                                } else {
                                    Log.w(TAG, "No long-term secret found, skipping server unpair")
                                }
                            } catch (e: Exception) {
                                Log.e(TAG, "Failed to unpair from server: ${e.message}")
                                // Continue with local unpair even if server call fails
                            }
                            
                            // Clear local pairing data
                            pairingPrefs.clearPairing()
                            isPaired = false
                            deviceName = null
                            sessionId = null
                            showUnpairDialog = false
                        }
                    },
                    colors = ButtonDefaults.textButtonColors(
                        contentColor = MaterialTheme.colorScheme.error
                    )
                ) {
                    Text("Unpair")
                }
            },
            dismissButton = {
                TextButton(onClick = { showUnpairDialog = false }) {
                    Text("Cancel")
                }
            }
        )
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
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // Top spacer to push content to center
            Spacer(modifier = Modifier.weight(1f))
            
            // Main content
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Image(
                    painter = painterResource(id = R.drawable.imagetools_logo),
                    contentDescription = "ImageTools Logo",
                    modifier = Modifier.size(120.dp)
                )
                
                Spacer(modifier = Modifier.height(24.dp))
                
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
                        text = "You can now share images from your Gallery to Image Tools",
                        style = MaterialTheme.typography.bodyMedium,
                        textAlign = TextAlign.Center
                    )
                    
                    Spacer(modifier = Modifier.height(24.dp))
                    
                    Button(
                        onClick = { showUnpairDialog = true },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.error
                        )
                    ) {
                        Text("Unpair Device")
                    }
                } else {
                    Text(
                        text = "Scan the QR code from your Image Tools session",
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
                }
            }
            
            // Bottom spacer to push content to center
            Spacer(modifier = Modifier.weight(1f))
            
            // Version info at bottom
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Text(
                    text = BuildConfig.VERSION_INFO,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center
                )
                Text(
                    text = "Built: ${BuildConfig.BUILD_TIME}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center
                )
            }
        }
    }
}
