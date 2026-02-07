package com.imagetools.mobile.data.models

import com.google.gson.annotations.SerializedName

/**
 * Data class representing the QR code payload scanned from Image Tools web app
 */
data class QRCodeData(
    @SerializedName("instance_url")
    val instanceUrl: String,
    
    @SerializedName("shared_secret")
    val sharedSecret: String,
    
    @SerializedName("pairing_id")
    val pairingId: String,
    
    @SerializedName("session_id")
    val sessionId: String
)
