package com.imagetools.mobile.utils

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

// Extension property for DataStore
private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "pairing_prefs")

/**
 * Manages pairing preferences using DataStore
 */
class PairingPreferences(private val context: Context) {
    
    companion object {
        private val INSTANCE_URL_KEY = stringPreferencesKey("instance_url")
        private val SHARED_SECRET_KEY = stringPreferencesKey("shared_secret")
        private val PAIRING_ID_KEY = stringPreferencesKey("pairing_id")
        private val SESSION_ID_KEY = stringPreferencesKey("session_id")
        private val DEVICE_NAME_KEY = stringPreferencesKey("device_name")
        private val LONG_TERM_SECRET_KEY = stringPreferencesKey("long_term_secret")
        private val REFRESH_SECRET_KEY = stringPreferencesKey("refresh_secret")
        private val LONG_TERM_EXPIRES_AT_KEY = stringPreferencesKey("long_term_expires_at")
        private val REFRESH_EXPIRES_AT_KEY = stringPreferencesKey("refresh_expires_at")
    }
    
    /**
     * Save pairing data with long-term authorization
     */
    suspend fun savePairing(
        instanceUrl: String,
        sharedSecret: String,
        pairingId: String,
        sessionId: String,
        deviceName: String,
        longTermSecret: String,
        refreshSecret: String,
        longTermExpiresAt: String,
        refreshExpiresAt: String
    ) {
        context.dataStore.edit { prefs ->
            prefs[INSTANCE_URL_KEY] = instanceUrl
            prefs[SHARED_SECRET_KEY] = sharedSecret
            prefs[PAIRING_ID_KEY] = pairingId
            prefs[SESSION_ID_KEY] = sessionId
            prefs[DEVICE_NAME_KEY] = deviceName
            prefs[LONG_TERM_SECRET_KEY] = longTermSecret
            prefs[REFRESH_SECRET_KEY] = refreshSecret
            prefs[LONG_TERM_EXPIRES_AT_KEY] = longTermExpiresAt
            prefs[REFRESH_EXPIRES_AT_KEY] = refreshExpiresAt
        }
    }
    
    /**
     * Get instance URL
     */
    val instanceUrl: Flow<String?> = context.dataStore.data
        .map { prefs -> prefs[INSTANCE_URL_KEY] }
    
    /**
     * Get shared secret
     */
    val sharedSecret: Flow<String?> = context.dataStore.data
        .map { prefs -> prefs[SHARED_SECRET_KEY] }
    
    /**
     * Get pairing ID
     */
    val pairingId: Flow<String?> = context.dataStore.data
        .map { prefs -> prefs[PAIRING_ID_KEY] }
    
    /**
     * Get session ID
     */
    val sessionId: Flow<String?> = context.dataStore.data
        .map { prefs -> prefs[SESSION_ID_KEY] }
    
    /**
     * Get device name
     */
    val deviceName: Flow<String?> = context.dataStore.data
        .map { prefs -> prefs[DEVICE_NAME_KEY] }
    
    /**
     * Get long-term secret
     */
    val longTermSecret: Flow<String?> = context.dataStore.data
        .map { prefs -> prefs[LONG_TERM_SECRET_KEY] }
    
    /**
     * Get refresh secret
     */
    val refreshSecret: Flow<String?> = context.dataStore.data
        .map { prefs -> prefs[REFRESH_SECRET_KEY] }
    
    /**
     * Get long-term expiration date
     */
    val longTermExpiresAt: Flow<String?> = context.dataStore.data
        .map { prefs -> prefs[LONG_TERM_EXPIRES_AT_KEY] }
    
    /**
     * Get refresh expiration date
     */
    val refreshExpiresAt: Flow<String?> = context.dataStore.data
        .map { prefs -> prefs[REFRESH_EXPIRES_AT_KEY] }
    
    /**
     * Check if paired (has valid long-term secret)
     */
    val isPaired: Flow<Boolean> = context.dataStore.data
        .map { prefs -> 
            prefs[INSTANCE_URL_KEY] != null && 
            prefs[LONG_TERM_SECRET_KEY] != null 
        }
    
    /**
     * Clear all pairing data
     */
    suspend fun clearPairing() {
        context.dataStore.edit { prefs ->
            prefs.clear()
        }
    }
}
