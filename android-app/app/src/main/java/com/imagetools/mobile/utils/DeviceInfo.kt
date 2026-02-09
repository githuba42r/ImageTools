package com.imagetools.mobile.utils

import android.Manifest
import android.accounts.AccountManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat

/**
 * Utility for retrieving device owner information
 */
object DeviceInfo {
    
    /**
     * Get the device owner name
     * 
     * Attempts to retrieve the owner name from:
     * 1. Google account (requires GET_ACCOUNTS permission)
     * 2. Build.USER (fallback, often unreliable)
     * 3. "Unknown" if neither is available
     * 
     * @param context Android context
     * @return Owner name or "Unknown"
     */
    fun getDeviceOwner(context: Context): String {
        // Try to get Google account name if permission is granted
        if (hasAccountsPermission(context)) {
            try {
                val accountManager = AccountManager.get(context)
                val accounts = accountManager.getAccountsByType("com.google")
                
                if (accounts.isNotEmpty()) {
                    // Return first Google account name
                    val email = accounts[0].name
                    // Extract name before @ if it's an email
                    return email.substringBefore("@")
                }
            } catch (e: Exception) {
                // Permission might be revoked or other error occurred
                // Fall through to next option
            }
        }
        
        // Fallback to Build.USER if it looks useful
        val buildUser = Build.USER
        if (buildUser.isNotBlank() && !isSystemUsername(buildUser)) {
            return buildUser
        }
        
        // No owner information available
        return "Unknown"
    }
    
    /**
     * Check if GET_ACCOUNTS permission is granted
     */
    fun hasAccountsPermission(context: Context): Boolean {
        return ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.GET_ACCOUNTS
        ) == PackageManager.PERMISSION_GRANTED
    }
    
    /**
     * Check if a username is a common system/build username
     * that shouldn't be shown as the owner name
     */
    private fun isSystemUsername(username: String): Boolean {
        val systemUsernames = setOf(
            "dpi",
            "user",
            "root",
            "shell",
            "system",
            "android-build",
            "nobody"
        )
        return username.lowercase() in systemUsernames
    }
}
