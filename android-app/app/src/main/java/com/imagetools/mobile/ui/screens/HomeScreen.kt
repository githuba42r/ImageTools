package com.imagetools.mobile.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.imagetools.mobile.BuildConfig
import com.imagetools.mobile.utils.PairingPreferences
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

@Composable
fun HomeScreen(pairingPrefs: PairingPreferences) {
    var isPaired by remember { mutableStateOf(false) }
    var deviceName by remember { mutableStateOf<String?>(null) }
    var sessionId by remember { mutableStateOf<String?>(null) }
    var showScanner by remember { mutableStateOf(false) }
    var showUnpairDialog by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    
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
