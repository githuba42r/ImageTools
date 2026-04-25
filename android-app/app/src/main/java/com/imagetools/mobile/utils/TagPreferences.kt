package com.imagetools.mobile.utils

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.tagDataStore: DataStore<Preferences> by preferencesDataStore(name = "tag_prefs")

class TagPreferences(private val context: Context) {
    companion object {
        private val CURRENT_TAG_KEY = stringPreferencesKey("current_tag")
    }

    val currentTag: Flow<String?> =
        context.tagDataStore.data.map { it[CURRENT_TAG_KEY]?.takeIf { s -> s.isNotBlank() } }

    suspend fun getCurrentTag(): String? = currentTag.first()

    suspend fun setCurrentTag(tag: String?) {
        context.tagDataStore.edit { prefs ->
            val trimmed = tag?.trim().orEmpty()
            if (trimmed.isEmpty()) prefs.remove(CURRENT_TAG_KEY)
            else prefs[CURRENT_TAG_KEY] = trimmed
        }
    }
}
