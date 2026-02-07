package com.imagetools.mobile

import android.content.Intent
import android.net.Uri
import android.os.Bundle
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
import com.imagetools.mobile.data.network.RetrofitClient
import com.imagetools.mobile.utils.PairingPreferences
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.io.FileOutputStream
import java.io.IOException

class ShareActivity : ComponentActivity() {
    
    private lateinit var pairingPrefs: PairingPreferences
    private var statusText by mutableStateOf("Uploading image...")
    private var isError by mutableStateOf(false)
    private var uploadedCount by mutableStateOf(0)
    private var totalCount by mutableStateOf(0)
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        pairingPrefs = PairingPreferences(this)
        
        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
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
                                text = statusText,
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
            }
        }
        
        handleSharedImage(intent)
    }
    
    private fun handleSharedImage(intent: Intent?) {
        when {
            // Single image
            intent?.action == Intent.ACTION_SEND && intent.type?.startsWith("image/") == true -> {
                val imageUri = intent.getParcelableExtra<Uri>(Intent.EXTRA_STREAM)
                if (imageUri != null) {
                    totalCount = 1
                    uploadImage(imageUri)
                } else {
                    showError("No image found")
                }
            }
            // Multiple images
            intent?.action == Intent.ACTION_SEND_MULTIPLE && intent.type?.startsWith("image/") == true -> {
                val imageUris = intent.getParcelableArrayListExtra<Uri>(Intent.EXTRA_STREAM)
                if (imageUris != null && imageUris.isNotEmpty()) {
                    totalCount = imageUris.size
                    statusText = "Uploading ${totalCount} images..."
                    uploadMultipleImages(imageUris)
                } else {
                    showError("No images found")
                }
            }
            else -> {
                showError("Invalid share intent")
            }
        }
    }
    
    private fun uploadMultipleImages(imageUris: List<Uri>) {
        lifecycleScope.launch {
            for ((index, uri) in imageUris.withIndex()) {
                try {
                    uploadedCount = index
                    statusText = "Uploading image ${index + 1} of ${totalCount}..."
                    uploadImageSync(uri)
                } catch (e: Exception) {
                    showError("Failed to upload image ${index + 1}: ${e.message}")
                    return@launch
                }
            }
            // All uploaded successfully
            uploadedCount = totalCount
            showSuccess("${totalCount} images uploaded successfully!")
        }
    }
    
    private fun uploadImage(imageUri: Uri) {
        lifecycleScope.launch {
            try {
                uploadImageSync(imageUri)
                showSuccess("Image uploaded successfully!")
            } catch (e: IOException) {
                showError("Network error: ${e.message}")
            } catch (e: Exception) {
                showError("Error: ${e.message}")
            }
        }
    }
    
    private suspend fun uploadImageSync(imageUri: Uri) {
        val longTermSecret = pairingPrefs.longTermSecret.first()
        val instanceUrl = pairingPrefs.instanceUrl.first()
        
        if (longTermSecret == null || instanceUrl == null) {
            throw Exception("Not paired. Open app and scan QR code first.")
        }
        
        RetrofitClient.setBaseUrl(instanceUrl)
        
        // Copy URI content to a temporary file
        val inputStream = contentResolver.openInputStream(imageUri)
            ?: throw IOException("Failed to read image")
        
        val tempFile = File(cacheDir, "temp_upload_${System.currentTimeMillis()}.jpg")
        val outputStream = FileOutputStream(tempFile)
        inputStream.copyTo(outputStream)
        inputStream.close()
        outputStream.close()
        
        // Get filename
        val filename = getFileName(imageUri) ?: "shared_image.jpg"
        
        // Create multipart request with long-term secret
        val requestFile = tempFile.asRequestBody("image/*".toMediaTypeOrNull())
        val filePart = MultipartBody.Part.createFormData("file", filename, requestFile)
        val secretPart = longTermSecret.toRequestBody("text/plain".toMediaTypeOrNull())
        
        // Upload
        val response = RetrofitClient.getApi().uploadImage(secretPart, filePart)
        
        // Clean up temp file
        tempFile.delete()
        
        if (!response.isSuccessful) {
            val errorBody = response.errorBody()?.string()
            throw Exception("Upload failed: ${response.code()} - $errorBody")
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
        statusText = message
        isError = true
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }
}
