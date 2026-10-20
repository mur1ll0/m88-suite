package com.m88suite.app

import android.Manifest
import android.app.Application
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Dashboard
import androidx.compose.material.icons.rounded.MoreHoriz
import androidx.compose.material.icons.rounded.PhotoLibrary
import androidx.compose.material.icons.rounded.Videocam
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewmodel.compose.viewModel
import com.m88suite.app.device.DeviceManager
import com.m88suite.app.ui.CameraScreen
import com.m88suite.app.ui.DashboardScreen
import com.m88suite.app.ui.M88Theme
import com.m88suite.app.ui.MediaScreen
import com.m88suite.app.ui.MoreScreen
import com.m88suite.app.ui.Palette
import com.m88suite.core.LinkState

/** Mantem o DeviceManager vivo entre rotacoes de tela. */
class DeviceViewModel(app: Application) : AndroidViewModel(app) {
    val manager = DeviceManager(app)
    override fun onCleared() = manager.close()
}

class MainActivity : ComponentActivity() {
    private val permissions = arrayOf(
        Manifest.permission.BLUETOOTH_SCAN,
        Manifest.permission.BLUETOOTH_CONNECT,
        Manifest.permission.NEARBY_WIFI_DEVICES,
        Manifest.permission.ACCESS_FINE_LOCATION,
    )
    private var onPermissions: () -> Unit = {}
    private val request = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
        if (result.values.all { it }) onPermissions()
    }

    private fun withPermissions(action: () -> Unit) {
        if (permissions.all { ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED }) {
            action()
        } else {
            onPermissions = action
            request.launch(permissions)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            M88Theme {
                val vm: DeviceViewModel = viewModel()
                val manager = vm.manager
                val t by manager.telemetry.collectAsState()
                val log = remember { mutableStateListOf<String>() }
                var tab by remember { mutableStateOf(0) }
                var mediaStatus by remember { mutableStateOf("") }
                var syncing by remember { mutableStateOf(false) }

                LaunchedEffect(Unit) {
                    withPermissions { manager.connect() }
                    manager.log.collect { log.add(it); if (log.size > 100) log.removeAt(0) }
                }
                val tabs = listOf(
                    "Painel" to Icons.Rounded.Dashboard,
                    "Câmera" to Icons.Rounded.Videocam,
                    "Mídia" to Icons.Rounded.PhotoLibrary,
                    "Mais" to Icons.Rounded.MoreHoriz,
                )
                Scaffold(containerColor = Palette.Bg, bottomBar = {
                    NavigationBar(containerColor = Palette.Surface) {
                        tabs.forEachIndexed { i, (label, icon) ->
                            NavigationBarItem(selected = tab == i, onClick = { tab = i },
                                icon = { Icon(icon, null) }, label = { Text(label) })
                        }
                    }
                }) { padding ->
                    val modifier = Modifier.padding(padding)
                    androidx.compose.foundation.layout.Box(modifier) {
                        when (tab) {
                            0 -> DashboardScreen(t, log,
                                onConnectToggle = { if (t.link == LinkState.DISCONNECTED) withPermissions { manager.connect() } else manager.disconnect() },
                                onRestart = { manager.restartDevice() })
                            1 -> CameraScreen(t, manager.video, onStart = { cfg -> withPermissions { manager.startStream(cfg) } },
                                onStop = { manager.stopStream() })
                            2 -> MediaScreen(t.mediaCount, mediaStatus, syncing) {
                                syncing = true
                                withPermissions {
                                    manager.syncMedia { msg ->
                                        runOnUiThread {
                                            mediaStatus = msg
                                            if (msg.startsWith("Sincronizado") || msg.startsWith("Falha")) syncing = false
                                        }
                                    }
                                }
                            }
                            else -> MoreScreen()
                        }
                    }
                }
            }
        }
    }
}
