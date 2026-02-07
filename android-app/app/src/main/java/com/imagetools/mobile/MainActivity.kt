package com.imagetools.mobile

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Log
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
    private val pendingPairingData = mutableStateOf<PairingData?>(null)
    
    data class PairingData(
        val url: String,
        val secret: String,
        val pairingId: String,
        val sessionId: String
    )
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        pairingPrefs = PairingPreferences(this)
        
        // Check if launched from deep link
        handleIntent(intent)
        
        setContent {
            val currentPairingData by pendingPairingData
            
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    HomeScreen(
                        pairingPrefs = pairingPrefs,
                        pendingPairingData = currentPairingData?.let {
                            mapOf(
                                "url" to it.url,
                                "secret" to it.secret,
                                "pairing_id" to it.pairingId,
                                "session_id" to it.sessionId
                            )
                        }
                    )
                }
            }
        }
    }
    
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }
    
    private fun handleIntent(intent: Intent?) {
        val data: Uri? = intent?.data
        
        if (data != null && data.scheme == "imagetools" && data.host == "pair") {
            Log.d("MainActivity", "Deep link received: $data")
            Log.d("MainActivity", "Full URI: ${data.toString()}")
            Log.d("MainActivity", "Scheme: ${data.scheme}, Host: ${data.host}, Path: ${data.path}")
            Log.d("MainActivity", "Query string: ${data.query}")
            Log.d("MainActivity", "Encoded query: ${data.encodedQuery}")
            
            val url = data.getQueryParameter("url")
            val secret = data.getQueryParameter("secret")
            val pairingId = data.getQueryParameter("pairing_id")
            val sessionId = data.getQueryParameter("session_id")
            
            Log.d("MainActivity", "Parsed parameters: url=$url, secret=${secret?.take(20)}..., pairingId=$pairingId, sessionId=$sessionId")
            
            if (url != null && secret != null && pairingId != null && sessionId != null) {
                Log.d("MainActivity", "Valid pairing data received")
                pendingPairingData.value = PairingData(url, secret, pairingId, sessionId)
            } else {
                Log.e("MainActivity", "Invalid pairing data: url=$url, secret=$secret, pairingId=$pairingId, sessionId=$sessionId")
            }
        }
    }
}
