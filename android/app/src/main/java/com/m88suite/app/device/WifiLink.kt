package com.m88suite.app.device

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.wifi.WifiNetworkSpecifier
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.withTimeoutOrNull

/**
 * Rede Wi-Fi local do oculos (AP M88-522B, sem internet). Os sockets do oculos usam `network`
 * explicitamente; o resto do celular continua com a internet normal.
 */
class WifiLink(context: Context) {
    companion object {
        const val SSID = "M88-522B"
        const val PASSWORD = "12345678"
        const val DEVICE_IP = "192.168.48.1"
    }

    private val cm = context.getSystemService(ConnectivityManager::class.java)
    private var callback: ConnectivityManager.NetworkCallback? = null

    @Volatile
    var network: Network? = null
        private set

    /** Pede a rede ao Android (o sistema mostra a confirmacao na primeira vez). */
    suspend fun connect(timeoutMs: Long = 40_000): Network {
        network?.let { return it }
        release()
        val ready = CompletableDeferred<Network>()
        val cb = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(n: Network) {
                network = n
                ready.complete(n)
            }

            override fun onLost(n: Network) {
                if (network == n) network = null
            }

            override fun onUnavailable() {
                ready.completeExceptionally(IllegalStateException("rede $SSID nao encontrada"))
            }
        }
        val specifier = WifiNetworkSpecifier.Builder()
            .setSsid(SSID)
            .setIsHiddenSsid(true)
            .setWpa2Passphrase(PASSWORD)
            .build()
        val request = NetworkRequest.Builder()
            .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            .removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .setNetworkSpecifier(specifier)
            .build()
        callback = cb
        cm.requestNetwork(request, cb, timeoutMs.toInt())
        return withTimeoutOrNull(timeoutMs + 2_000) { ready.await() }
            ?: throw IllegalStateException("tempo esgotado conectando em $SSID")
    }

    fun release() {
        callback?.let { runCatching { cm.unregisterNetworkCallback(it) } }
        callback = null
        network = null
    }
}
