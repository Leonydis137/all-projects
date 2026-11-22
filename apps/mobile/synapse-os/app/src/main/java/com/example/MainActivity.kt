package com.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.*
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.zIndex
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.roundToInt

class SynapseViewModel : ViewModel() {
    var isBooted by mutableStateOf(false)
    var apiKey by mutableStateOf("")

    class WindowData(
        val id: String,
        val title: String,
        val icon: String,
        val initialWidth: Dp,
        val initialHeight: Dp,
        val initialX: Float = 50f,
        val initialY: Float = 50f
    ) {
        var x by mutableStateOf(initialX)
        var y by mutableStateOf(initialY)
        var isOpen by mutableStateOf(false)
        var isMinimized by mutableStateOf(false)
        var zIndex by mutableStateOf(0)
    }

    val windows = listOf(
        WindowData("mesh", "Mesh_Aperture // Live_Topology", "Σ", 600.dp, 450.dp, 100f, 100f),
        WindowData("hal", "HAL_Hardware_Diagnostics", ">_", 450.dp, 350.dp, 200f, 150f),
        WindowData("term", "Sovereign_CLI_Terminal", "~", 500.dp, 350.dp, 300f, 200f),
        WindowData("vault", "Security Vault", "🛡", 350.dp, 250.dp, 400f, 250f)
    )

    fun openWindow(id: String) {
        val win = windows.find { it.id == id } ?: return
        win.isOpen = true
        win.isMinimized = false
        bringToFront(id)
    }

    fun toggleMinimize(id: String) {
        val win = windows.find { it.id == id } ?: return
        win.isMinimized = !win.isMinimized
        if (!win.isMinimized) bringToFront(id)
    }

    fun closeWindow(id: String) {
        windows.find { it.id == id }?.isOpen = false
    }

    fun bringToFront(id: String) {
        val maxZ = windows.maxOfOrNull { it.zIndex } ?: 0
        windows.find { it.id == id }?.zIndex = maxZ + 1
    }
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MyApplicationTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    SynapseApp(modifier = Modifier.padding(innerPadding))
                }
            }
        }
    }
}

@Composable
fun SynapseApp(modifier: Modifier = Modifier, viewModel: SynapseViewModel = viewModel()) {
    Box(modifier = modifier.fillMaxSize().background(BackgroundDark)) {
        AnimatedVisibility(
            visible = !viewModel.isBooted,
            exit = slideOutVertically(animationSpec = tween(800)) { -it } + fadeOut(animationSpec = tween(800))
        ) {
            LockoutScreen(viewModel)
        }

        AnimatedVisibility(
            visible = viewModel.isBooted,
            enter = fadeIn(animationSpec = tween(1000, delayMillis = 500))
        ) {
            DesktopScreen(viewModel)
        }
    }
}

@Composable
fun LockoutScreen(viewModel: SynapseViewModel) {
    val coroutineScope = rememberCoroutineScope()
    var terminalText by remember { mutableStateOf("> Awaiting cryptographic token...") }
    
    Column(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        // Logo
        Box(
            modifier = Modifier
                .size(96.dp)
                .border(2.dp, Zinc900, CircleShape)
                .padding(8.dp),
            contentAlignment = Alignment.Center
        ) {
            Text("Σ", color = AccentMain, fontSize = 48.sp, fontWeight = FontWeight.Black)
        }
        
        Spacer(modifier = Modifier.height(32.dp))
        
        Text("Sovereign Shell v16.0", color = Color.White, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Black, fontSize = 24.sp, letterSpacing = 2.sp)
        Text("Hardware & AI Singularity", color = Zinc500, fontFamily = FontFamily.Monospace, fontSize = 12.sp, letterSpacing = 4.sp)
        
        Spacer(modifier = Modifier.height(48.dp))
        
        Column(
            modifier = Modifier
                .width(400.dp)
                .background(Color.Black.copy(alpha = 0.5f), RoundedCornerShape(24.dp))
                .border(1.dp, Zinc900, RoundedCornerShape(24.dp))
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            OutlinedTextField(
                value = viewModel.apiKey,
                onValueChange = { viewModel.apiKey = it },
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text("GEMINI_API_KEY (AIza...)", fontFamily = FontFamily.Monospace, fontSize = 12.sp, color = Zinc800) },
                textStyle = LocalTextStyle.current.copy(fontFamily = FontFamily.Monospace, textAlign = TextAlign.Center, color = AccentMain),
                singleLine = true,
                visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Go),
                keyboardActions = KeyboardActions(onGo = {
                    coroutineScope.launch {
                        terminalText = "> Validating..."
                        delay(500)
                        terminalText = "> Token Accepted. Mounting File System..."
                        delay(500)
                        viewModel.isBooted = true
                    }
                }),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = AccentMain,
                    unfocusedBorderColor = Zinc800,
                    cursorColor = AccentMain
                ),
                shape = RoundedCornerShape(16.dp)
            )
            
            Spacer(modifier = Modifier.height(20.dp))
            
            Button(
                onClick = {
                    coroutineScope.launch {
                        terminalText = "> Validating..."
                        delay(600)
                        terminalText = "> Token Accepted. Mounting Root..."
                        delay(600)
                        viewModel.isBooted = true
                    }
                },
                modifier = Modifier.fillMaxWidth().height(56.dp),
                shape = RoundedCornerShape(16.dp),
                colors = ButtonDefaults.buttonColors(containerColor = AccentMain, contentColor = Color.Black)
            ) {
                Text("MOUNT FILE SYSTEM", fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Black, fontSize = 12.sp, letterSpacing = 2.sp)
            }
        }
        
        Spacer(modifier = Modifier.height(32.dp))
        
        Text(terminalText, color = Zinc500, fontFamily = FontFamily.Monospace, fontSize = 12.sp)
    }
}

@Composable
fun DesktopScreen(viewModel: SynapseViewModel) {
    Box(modifier = Modifier.fillMaxSize()) {
        // App Icons
        Column(modifier = Modifier.padding(32.dp).padding(top = 16.dp)) {
            viewModel.windows.forEach { win ->
                AppIcon(win.icon, win.id) { viewModel.openWindow(win.id) }
                Spacer(modifier = Modifier.height(16.dp))
            }
        }
        
        // Windows
        viewModel.windows.filter { it.isOpen }.sortedBy { it.zIndex }.forEach { win ->
            val scale by animateFloatAsState(if (win.isMinimized) 0f else 1f, label = "win_scale")
            val alphaAnim by animateFloatAsState(if (win.isMinimized) 0f else 1f, label = "win_alpha")
            
            if (scale > 0.01f) {
                Box(modifier = Modifier
                    .offset { IntOffset(win.x.roundToInt(), win.y.roundToInt()) }
                    .zIndex(win.zIndex.toFloat())
                    .scale(scale)
                    .alpha(alphaAnim)
                ) {
                    WindowComponent(win, viewModel)
                }
            }
        }
        
        // Taskbar
        Taskbar(viewModel, modifier = Modifier.align(Alignment.BottomCenter))
    }
}

@Composable
fun AppIcon(icon: String, label: String, onClick: () -> Unit) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.clickable { onClick() }.padding(8.dp).width(80.dp)
    ) {
        Box(
            modifier = Modifier
                .size(64.dp)
                .clip(RoundedCornerShape(16.dp))
                .background(Zinc900)
                .border(1.dp, Zinc800, RoundedCornerShape(16.dp)),
            contentAlignment = Alignment.Center
        ) {
            Text(icon, color = AccentMain, fontSize = 32.sp, fontWeight = FontWeight.Black, fontFamily = FontFamily.Monospace)
        }
        Spacer(modifier = Modifier.height(8.dp))
        Text(label.uppercase(), color = Zinc400, fontSize = 10.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
    }
}

@Composable
fun WindowComponent(win: SynapseViewModel.WindowData, viewModel: SynapseViewModel) {
    Column(
        modifier = Modifier
            .width(win.initialWidth)
            .height(win.initialHeight)
            .clip(RoundedCornerShape(24.dp))
            .background(PanelDark)
            .border(1.dp, BorderDark, RoundedCornerShape(24.dp))
            .clickable { viewModel.bringToFront(win.id) }
    ) {
        // Header
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color.Black.copy(alpha = 0.45f))
                .border(1.dp, BorderDark)
                .pointerInput(Unit) {
                    detectDragGestures(
                        onDragStart = { viewModel.bringToFront(win.id) }
                    ) { change, dragAmount ->
                        change.consume()
                        win.x += dragAmount.x
                        win.y += dragAmount.y
                    }
                }
                .padding(horizontal = 22.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(modifier = Modifier.size(8.dp).background(SuccessGreen, CircleShape))
                Spacer(modifier = Modifier.width(16.dp))
                Text(win.title, color = Zinc400, fontFamily = FontFamily.Monospace, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 2.sp)
            }
            Row {
                Text("—", color = Zinc500, fontSize = 14.sp, modifier = Modifier.clickable { viewModel.toggleMinimize(win.id) }.padding(horizontal = 8.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text("✕", color = Zinc500, fontSize = 14.sp, modifier = Modifier.clickable { viewModel.closeWindow(win.id) }.padding(start = 8.dp))
            }
        }
        
        // Content
        Box(modifier = Modifier.fillMaxSize().padding(24.dp)) {
            when (win.id) {
                "mesh" -> MeshApp()
                "hal" -> HalApp()
                "term" -> TermApp()
                "vault" -> VaultApp()
            }
        }
    }
}

@Composable
fun Taskbar(viewModel: SynapseViewModel, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .height(60.dp)
            .background(Color(0xFA050505))
            .border(1.dp, BorderDark)
            .padding(horizontal = 24.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        viewModel.windows.filter { it.isOpen }.forEach { win ->
            val isActive = win.zIndex == (viewModel.windows.maxOfOrNull { it.zIndex } ?: 0) && !win.isMinimized
            val bg = if (isActive) AccentMain.copy(alpha = 0.2f) else Color.Transparent
            val border = if (isActive) AccentDim else Color.Transparent
            val textCol = if (isActive) Color.White else Zinc400
            
            Row(
                modifier = Modifier
                    .padding(end = 14.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(bg)
                    .border(1.dp, border, RoundedCornerShape(12.dp))
                    .clickable { 
                        if (win.isMinimized) viewModel.toggleMinimize(win.id)
                        else if (!isActive) viewModel.bringToFront(win.id)
                        else viewModel.toggleMinimize(win.id)
                    }
                    .padding(horizontal = 14.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(win.icon, color = textCol, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                Spacer(modifier = Modifier.width(8.dp))
                Text(win.id.uppercase(), color = textCol, fontSize = 10.sp, fontFamily = FontFamily.Monospace, letterSpacing = 1.sp)
            }
        }
    }
}

// ---- APP CONTENTS ----

@Composable
fun MeshApp() {
    Row(modifier = Modifier.fillMaxSize()) {
        Box(modifier = Modifier.weight(2f).fillMaxHeight().background(Color.Black.copy(alpha = 0.6f), RoundedCornerShape(16.dp)).border(1.dp, BorderDark, RoundedCornerShape(16.dp)), contentAlignment = Alignment.Center) {
            Text("[Live Topology Offline]", color = Zinc500, fontFamily = FontFamily.Monospace, fontSize = 12.sp)
        }
        Spacer(modifier = Modifier.width(16.dp))
        Column(modifier = Modifier.weight(1f).fillMaxHeight()) {
            Column(modifier = Modifier.fillMaxWidth().background(Color.White.copy(alpha = 0.012f), RoundedCornerShape(16.dp)).border(1.dp, BorderDark, RoundedCornerShape(16.dp)).padding(16.dp)) {
                Text("NETWORK DOWNLINK", color = Zinc500, fontFamily = FontFamily.Monospace, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 2.sp)
                Text("1,402.8", color = Color.White, fontFamily = FontFamily.Monospace, fontSize = 48.sp, fontWeight = FontWeight.Light, modifier = Modifier.padding(top = 8.dp))
                Text("PHYSICAL MBPS", color = Zinc500, fontFamily = FontFamily.Monospace, fontSize = 10.sp, fontWeight = FontWeight.Bold)
            }
            Spacer(modifier = Modifier.height(16.dp))
            Column(modifier = Modifier.fillMaxWidth().weight(1f).background(Color.White.copy(alpha = 0.012f), RoundedCornerShape(16.dp)).border(1.dp, BorderDark, RoundedCornerShape(16.dp)).padding(16.dp)) {
                Text("NEURAL DIRECTIVE", color = Zinc500, fontFamily = FontFamily.Monospace, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 2.sp)
                OutlinedTextField(
                    value = "", onValueChange = {},
                    placeholder = { Text("Enter intent...", fontSize = 12.sp, color = Zinc500) },
                    modifier = Modifier.fillMaxSize().padding(top = 8.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        unfocusedBorderColor = Zinc800,
                        focusedBorderColor = AccentMain
                    )
                )
            }
        }
    }
}

@Composable
fun HalApp() {
    Column {
        Row(modifier = Modifier.weight(1f)) {
            HalCard("MEMORY", "3.2 GB", Modifier.weight(1f))
            Spacer(modifier = Modifier.width(16.dp))
            HalCard("CORE UNITS", "8 Logical", Modifier.weight(1f))
        }
        Spacer(modifier = Modifier.height(16.dp))
        Row(modifier = Modifier.weight(1f)) {
            HalCard("POWER STATE", "94%", Modifier.weight(1f))
            Spacer(modifier = Modifier.width(16.dp))
            HalCard("CLIENT IDENTITY", "AISTUDIO_NEXUS", Modifier.weight(1f))
        }
    }
}

@Composable
fun HalCard(title: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier = modifier.fillMaxHeight().background(Color.Black.copy(alpha = 0.4f), RoundedCornerShape(16.dp)).border(1.dp, BorderDark, RoundedCornerShape(16.dp)).padding(16.dp), verticalArrangement = Arrangement.Center) {
        Text(title, color = Zinc500, fontFamily = FontFamily.Monospace, fontSize = 10.sp, letterSpacing = 2.sp)
        Text(value, color = Color.White, fontFamily = FontFamily.Monospace, fontSize = 32.sp, modifier = Modifier.padding(top = 8.dp))
    }
}

@Composable
fun TermApp() {
    Column(modifier = Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.8f), RoundedCornerShape(12.dp)).padding(12.dp)) {
        Text("SYNAPSE OS v16.0 Terminal", color = SuccessGreen, fontFamily = FontFamily.Monospace, fontSize = 12.sp)
        Text("Type 'help' for available commands.", color = Zinc500, fontFamily = FontFamily.Monospace, fontSize = 12.sp)
        Row(modifier = Modifier.padding(top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("sys@sov:~$ ", color = AccentMain, fontFamily = FontFamily.Monospace, fontSize = 12.sp)
            Text("█", color = AccentMain, fontFamily = FontFamily.Monospace, fontSize = 12.sp)
        }
    }
}

@Composable
fun VaultApp() {
    Column(modifier = Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
        Text("🛡", fontSize = 48.sp)
        Spacer(modifier = Modifier.height(16.dp))
        Text("ENCRYPTED VOLUME", color = ErrorRed, fontFamily = FontFamily.Monospace, fontSize = 14.sp, fontWeight = FontWeight.Bold, letterSpacing = 2.sp)
        Text("Access strictly prohibited.", color = Zinc500, fontFamily = FontFamily.Monospace, fontSize = 12.sp, modifier = Modifier.padding(top = 8.dp))
    }
}
