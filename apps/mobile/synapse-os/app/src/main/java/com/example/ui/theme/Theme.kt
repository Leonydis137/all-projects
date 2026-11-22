package com.example.ui.theme

import android.os.Build
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val DarkColorScheme =
  darkColorScheme(
    primary = AccentMain,
    secondary = AccentDim,
    tertiary = CyanGlow,
    background = BackgroundDark,
    surface = PanelDark,
    onPrimary = BackgroundDark,
    onSecondary = BackgroundDark,
    onBackground = Zinc400,
    onSurface = Zinc400
  )

@Composable
fun MyApplicationTheme(
  content: @Composable () -> Unit,
) {
  MaterialTheme(colorScheme = DarkColorScheme, typography = Typography, content = content)
}
