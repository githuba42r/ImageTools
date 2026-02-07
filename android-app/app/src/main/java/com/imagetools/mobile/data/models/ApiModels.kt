package com.imagetools.mobile.data.models

import com.google.gson.annotations.SerializedName

/**
 * Request model for validating shared secret
 */
data class ValidateSecretRequest(
    @SerializedName("shared_secret")
    val sharedSecret: String
)

/**
 * Response model for secret validation with long-term authorization
 */
data class ValidateSecretResponse(
    @SerializedName("valid")
    val valid: Boolean,
    
    @SerializedName("pairing_id")
    val pairingId: String?,
    
    @SerializedName("session_id")
    val sessionId: String?,
    
    @SerializedName("device_name")
    val deviceName: String?,
    
    @SerializedName("long_term_secret")
    val longTermSecret: String?,
    
    @SerializedName("refresh_secret")
    val refreshSecret: String?,
    
    @SerializedName("long_term_expires_at")
    val longTermExpiresAt: String?,
    
    @SerializedName("refresh_expires_at")
    val refreshExpiresAt: String?
)

/**
 * Request model for uploading an image
 */
data class ImageUploadRequest(
    @SerializedName("shared_secret")
    val sharedSecret: String,
    
    @SerializedName("image_base64")
    val imageBase64: String,
    
    @SerializedName("filename")
    val filename: String
)

/**
 * Response model for image upload
 */
data class ImageUploadResponse(
    @SerializedName("image_id")
    val imageId: String,
    
    @SerializedName("filename")
    val filename: String,
    
    @SerializedName("size")
    val size: Int,
    
    @SerializedName("width")
    val width: Int,
    
    @SerializedName("height")
    val height: Int,
    
    @SerializedName("format")
    val format: String,
    
    @SerializedName("thumbnail_url")
    val thumbnailUrl: String,
    
    @SerializedName("image_url")
    val imageUrl: String,
    
    @SerializedName("uploaded_at")
    val uploadedAt: String
)

/**
 * Request model for refreshing long-term secret
 */
data class RefreshSecretRequest(
    @SerializedName("refresh_secret")
    val refreshSecret: String
)

/**
 * Response model for refresh operation
 */
data class RefreshSecretResponse(
    @SerializedName("long_term_secret")
    val longTermSecret: String,
    
    @SerializedName("long_term_expires_at")
    val longTermExpiresAt: String
)

/**
 * Request model for validating auth status
 */
data class ValidateAuthRequest(
    @SerializedName("long_term_secret")
    val longTermSecret: String
)

/**
 * Response model for auth validation
 */
data class ValidateAuthResponse(
    @SerializedName("valid")
    val valid: Boolean,
    
    @SerializedName("expires_at")
    val expiresAt: String?,
    
    @SerializedName("needs_refresh")
    val needsRefresh: Boolean
)
