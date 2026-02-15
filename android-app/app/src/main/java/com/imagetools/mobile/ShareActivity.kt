package com.imagetools.mobile

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.exifinterface.media.ExifInterface
import androidx.lifecycle.lifecycleScope
import com.imagetools.mobile.data.models.ValidateAuthRequest
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
import java.io.InputStream

private const val TAG = "ShareActivity"

class ShareActivity : ComponentActivity() {
    
    private lateinit var pairingPrefs: PairingPreferences
    private var statusText by mutableStateOf("Uploading image...")
    private var isError by mutableStateOf(false)
    private var uploadedCount by mutableStateOf(0)
    private var totalCount by mutableStateOf(0)
    
    // Pending URIs to upload after permission is granted
    private var pendingImageUris: List<Uri>? = null
    
    // Permission launcher for ACCESS_MEDIA_LOCATION
    private val mediaLocationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            Log.d(TAG, "ACCESS_MEDIA_LOCATION permission granted")
        } else {
            Log.w(TAG, "ACCESS_MEDIA_LOCATION permission denied - GPS data may not be available")
        }
        // Proceed with upload regardless of permission result
        pendingImageUris?.let { uris ->
            if (uris.size == 1) {
                uploadImage(uris[0])
            } else {
                uploadMultipleImages(uris)
            }
        }
        pendingImageUris = null
    }
    
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
                    checkPermissionAndUpload(listOf(imageUri))
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
                    checkPermissionAndUpload(imageUris)
                } else {
                    showError("No images found")
                }
            }
            else -> {
                showError("Invalid share intent")
            }
        }
    }
    
    /**
     * Check ACCESS_MEDIA_LOCATION permission and request if needed.
     * This is required on Android 10+ to access GPS data in images.
     */
    private fun checkPermissionAndUpload(imageUris: List<Uri>) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            // Android 10+ requires ACCESS_MEDIA_LOCATION for GPS data
            when {
                ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.ACCESS_MEDIA_LOCATION
                ) == PackageManager.PERMISSION_GRANTED -> {
                    // Permission already granted, proceed with upload
                    Log.d(TAG, "ACCESS_MEDIA_LOCATION already granted")
                    if (imageUris.size == 1) {
                        uploadImage(imageUris[0])
                    } else {
                        uploadMultipleImages(imageUris)
                    }
                }
                else -> {
                    // Request permission
                    Log.d(TAG, "Requesting ACCESS_MEDIA_LOCATION permission")
                    pendingImageUris = imageUris
                    mediaLocationPermissionLauncher.launch(Manifest.permission.ACCESS_MEDIA_LOCATION)
                }
            }
        } else {
            // Below Android 10, no special permission needed
            if (imageUris.size == 1) {
                uploadImage(imageUris[0])
            } else {
                uploadMultipleImages(imageUris)
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
    
    /**
     * Extract GPS metadata from an image URI.
     * 
     * On Android 10+, GPS data is stripped from shared content:// URIs for privacy.
     * We try multiple methods in order:
     * 1. Query MediaStore directly for latitude/longitude columns (may be deprecated)
     * 2. Get real file path from MediaStore and read EXIF directly from file
     * 3. Use setRequireOriginal() with ExifInterface
     * 4. Try regular ExifInterface as fallback
     * 
     * Returns a map with latitude, longitude, and altitude if available.
     */
    private fun extractGpsMetadata(imageUri: Uri): Map<String, String>? {
        Log.d(TAG, "Attempting to extract GPS from URI: $imageUri")
        
        // Method 1: Query MediaStore for GPS data
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            try {
                val gpsFromMediaStore = extractGpsFromMediaStore(imageUri)
                if (gpsFromMediaStore != null) {
                    Log.d(TAG, "GPS extracted from MediaStore query")
                    return gpsFromMediaStore
                }
            } catch (e: Exception) {
                Log.w(TAG, "MediaStore GPS query failed: ${e.message}")
            }
        }
        
        // Method 2: Get real file path and read EXIF directly
        try {
            val gpsFromFilePath = extractGpsFromFilePath(imageUri)
            if (gpsFromFilePath != null) {
                Log.d(TAG, "GPS extracted from file path")
                return gpsFromFilePath
            }
        } catch (e: Exception) {
            Log.w(TAG, "File path GPS extraction failed: ${e.message}")
        }
        
        // Method 3: Try setRequireOriginal with ExifInterface
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            try {
                val originalUri = MediaStore.setRequireOriginal(imageUri)
                val gpsFromOriginal = extractGpsFromExif(originalUri)
                if (gpsFromOriginal != null) {
                    Log.d(TAG, "GPS extracted using setRequireOriginal")
                    return gpsFromOriginal
                }
            } catch (e: SecurityException) {
                Log.w(TAG, "setRequireOriginal failed (permission denied): ${e.message}")
            } catch (e: Exception) {
                Log.w(TAG, "setRequireOriginal failed: ${e.message}")
            }
        }
        
        // Method 4: Try regular ExifInterface as fallback
        try {
            val gpsFromExif = extractGpsFromExif(imageUri)
            if (gpsFromExif != null) {
                Log.d(TAG, "GPS extracted from regular EXIF read")
                return gpsFromExif
            }
        } catch (e: Exception) {
            Log.w(TAG, "Regular EXIF read failed: ${e.message}")
        }
        
        Log.d(TAG, "No GPS coordinates found using any method")
        return null
    }
    
    /**
     * Query MediaStore directly for GPS coordinates.
     * Note: LATITUDE and LONGITUDE columns are deprecated in Android Q but may still work.
     */
    @androidx.annotation.RequiresApi(Build.VERSION_CODES.Q)
    private fun extractGpsFromMediaStore(imageUri: Uri): Map<String, String>? {
        // Only works for content:// URIs from MediaStore
        if (imageUri.scheme != "content") {
            return null
        }
        
        val projection = arrayOf(
            MediaStore.Images.Media.LATITUDE,
            MediaStore.Images.Media.LONGITUDE
        )
        
        return try {
            contentResolver.query(imageUri, projection, null, null, null)?.use { cursor ->
                if (cursor.moveToFirst()) {
                    val latIndex = cursor.getColumnIndex(MediaStore.Images.Media.LATITUDE)
                    val lonIndex = cursor.getColumnIndex(MediaStore.Images.Media.LONGITUDE)
                    
                    if (latIndex >= 0 && lonIndex >= 0) {
                        // Check if columns exist and have values
                        if (!cursor.isNull(latIndex) && !cursor.isNull(lonIndex)) {
                            val latitude = cursor.getDouble(latIndex)
                            val longitude = cursor.getDouble(lonIndex)
                            
                            // Validate coordinates (0,0 is unlikely to be a real location)
                            if (latitude != 0.0 || longitude != 0.0) {
                                val result = mutableMapOf<String, String>()
                                result["latitude"] = latitude.toString()
                                result["longitude"] = longitude.toString()
                                Log.d(TAG, "MediaStore GPS: lat=$latitude, lon=$longitude")
                                return@use result
                            }
                        }
                    }
                }
                null
            }
        } catch (e: Exception) {
            Log.w(TAG, "MediaStore query exception: ${e.message}")
            null
        }
    }
    
    /**
     * Try to get the real file path from MediaStore and read EXIF directly.
     * This may work on some devices where direct file access is allowed.
     */
    @Suppress("DEPRECATION")
    private fun extractGpsFromFilePath(imageUri: Uri): Map<String, String>? {
        if (imageUri.scheme != "content") {
            return null
        }
        
        // Try to get the _data column which contains the file path
        val projection = arrayOf(MediaStore.Images.Media.DATA)
        
        return try {
            contentResolver.query(imageUri, projection, null, null, null)?.use { cursor ->
                if (cursor.moveToFirst()) {
                    val dataIndex = cursor.getColumnIndex(MediaStore.Images.Media.DATA)
                    if (dataIndex >= 0) {
                        val filePath = cursor.getString(dataIndex)
                        if (filePath != null && File(filePath).exists()) {
                            Log.d(TAG, "Got real file path: $filePath")
                            // Read EXIF directly from file
                            val exif = ExifInterface(filePath)
                            val latLong = FloatArray(2)
                            if (exif.getLatLong(latLong)) {
                                val result = mutableMapOf<String, String>()
                                result["latitude"] = latLong[0].toString()
                                result["longitude"] = latLong[1].toString()
                                
                                val altitude = exif.getAltitude(Double.NaN)
                                if (!altitude.isNaN()) {
                                    result["altitude"] = altitude.toString()
                                }
                                
                                Log.d(TAG, "File path EXIF GPS: lat=${latLong[0]}, lon=${latLong[1]}")
                                return@use result
                            }
                        }
                    }
                }
                null
            }
        } catch (e: SecurityException) {
            Log.w(TAG, "Security exception accessing file path: ${e.message}")
            null
        } catch (e: Exception) {
            Log.w(TAG, "File path extraction exception: ${e.message}")
            null
        }
    }
    
    /**
     * Extract GPS metadata from a URI using ExifInterface.
     */
    private fun extractGpsFromExif(uri: Uri): Map<String, String>? {
        return try {
            contentResolver.openInputStream(uri)?.use { inputStream ->
                val exif = ExifInterface(inputStream)
                
                // Get GPS coordinates
                val latLong = FloatArray(2)
                if (exif.getLatLong(latLong)) {
                    val result = mutableMapOf<String, String>()
                    result["latitude"] = latLong[0].toString()
                    result["longitude"] = latLong[1].toString()
                    
                    // Get altitude if available
                    val altitude = exif.getAltitude(Double.NaN)
                    if (!altitude.isNaN()) {
                        result["altitude"] = altitude.toString()
                    }
                    
                    Log.d(TAG, "EXIF GPS: lat=${latLong[0]}, lon=${latLong[1]}, alt=$altitude")
                    result
                } else {
                    null
                }
            }
        } catch (e: SecurityException) {
            Log.w(TAG, "SecurityException reading EXIF: ${e.message}")
            null
        } catch (e: Exception) {
            Log.w(TAG, "EXIF read exception: ${e.message}")
            null
        }
    }
    
    /**
     * Open an input stream for the image, using setRequireOriginal on Android 10+
     * to preserve GPS data in the file.
     */
    private fun openImageInputStream(imageUri: Uri): InputStream? {
        return try {
            val uri = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                MediaStore.setRequireOriginal(imageUri)
            } else {
                imageUri
            }
            contentResolver.openInputStream(uri)
        } catch (e: SecurityException) {
            // Fall back to regular URI if setRequireOriginal fails
            Log.w(TAG, "setRequireOriginal failed, falling back to regular URI: ${e.message}")
            contentResolver.openInputStream(imageUri)
        }
    }
    
    private suspend fun uploadImageSync(imageUri: Uri) {
        val longTermSecret = pairingPrefs.longTermSecret.first()
        val instanceUrl = pairingPrefs.instanceUrl.first()
        
        if (longTermSecret == null || instanceUrl == null) {
            throw Exception("Not paired. Open app and scan QR code first.")
        }
        
        RetrofitClient.setBaseUrl(instanceUrl)
        
        // Validate pairing is still active before uploading
        try {
            Log.d(TAG, "Validating pairing before upload...")
            val validateResponse = RetrofitClient.getApi().validateAuth(
                ValidateAuthRequest(longTermSecret = longTermSecret)
            )
            
            if (validateResponse.isSuccessful) {
                val validationResult = validateResponse.body()
                if (validationResult?.valid == false) {
                    // Pairing was revoked
                    Log.w(TAG, "Pairing is no longer valid - clearing local data")
                    pairingPrefs.clearPairing()
                    throw Exception("This device was unpaired from the web interface. Please pair again.")
                }
            } else {
                Log.w(TAG, "Failed to validate pairing: ${validateResponse.code()}")
                throw Exception("Failed to validate pairing with server")
            }
        } catch (e: Exception) {
            if (e.message?.contains("unpaired") == true) {
                // Re-throw unpaired message
                throw e
            }
            // For other errors, log but continue with upload attempt
            Log.e(TAG, "Error validating pairing: ${e.message}")
            throw Exception("Network error: Could not validate pairing. Check your connection.")
        }
        
        // Extract GPS metadata BEFORE copying the file (need to use setRequireOriginal)
        val gpsMetadata = extractGpsMetadata(imageUri)
        
        // Copy URI content to a temporary file using setRequireOriginal to preserve EXIF/GPS
        val inputStream = openImageInputStream(imageUri)
            ?: throw IOException("Failed to read image")
        
        val tempFile = File(cacheDir, "temp_upload_${System.currentTimeMillis()}.jpg")
        val outputStream = FileOutputStream(tempFile)
        inputStream.copyTo(outputStream)
        inputStream.close()
        outputStream.close()
        
        // Get filename
        val filename = getFileName(imageUri) ?: "shared_image.jpg"
        
        // Create multipart request with long-term secret and GPS metadata
        val requestFile = tempFile.asRequestBody("image/*".toMediaTypeOrNull())
        val filePart = MultipartBody.Part.createFormData("file", filename, requestFile)
        val secretPart = longTermSecret.toRequestBody("text/plain".toMediaTypeOrNull())
        
        // Add GPS metadata as form fields if available
        val latitudePart = gpsMetadata?.get("latitude")?.toRequestBody("text/plain".toMediaTypeOrNull())
        val longitudePart = gpsMetadata?.get("longitude")?.toRequestBody("text/plain".toMediaTypeOrNull())
        val altitudePart = gpsMetadata?.get("altitude")?.toRequestBody("text/plain".toMediaTypeOrNull())
        
        // Upload with GPS metadata
        val response = RetrofitClient.getApi().uploadImage(
            longTermSecret = secretPart,
            file = filePart,
            latitude = latitudePart,
            longitude = longitudePart,
            altitude = altitudePart
        )
        
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
