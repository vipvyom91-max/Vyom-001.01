package com.pwpcb.manager;

import android.app.Activity;
import android.net.http.SslError;
import android.os.Bundle;
import android.view.KeyEvent;
import android.webkit.SslErrorHandler;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.LinearLayout;
import android.widget.TextView;

public class MainActivity extends Activity {

    private WebView webView;
    private static final String APP_URL = "http://127.0.0.1:5000";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);

        webView = new WebView(this);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.MATCH_PARENT);
        webView.setLayoutParams(lp);

        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setLoadWithOverviewMode(true);
        ws.setUseWideViewPort(true);
        ws.setCacheMode(WebSettings.LOAD_DEFAULT);
        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        ws.setMediaPlaybackRequiresUserGesture(false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                handler.proceed();
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    view.loadData(
                        "<html><body style='background:#0d0d1a;color:#fff;font-family:sans-serif;text-align:center;padding-top:60px'>" +
                        "<h2 style='color:#7c3aed'>⚠️ PW PCB Manager</h2>" +
                        "<p>Server not running.</p>" +
                        "<p style='color:#aaa;font-size:14px'>Start it in Termux:</p>" +
                        "<code style='background:#1a1a2e;padding:10px;display:block;margin:16px;border-radius:8px'>bash ~/Vyom-001.01/START.sh</code>" +
                        "<button onclick='location.reload()' style='background:#7c3aed;color:#fff;border:none;padding:12px 24px;border-radius:8px;font-size:16px;margin-top:16px'>🔄 Retry</button>" +
                        "</body></html>",
                        "text/html", "utf-8");
                }
            }
        });

        root.addView(webView);
        setContentView(root);
        webView.loadUrl(APP_URL);
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    protected void onResume() {
        super.onResume();
        webView.onResume();
    }

    @Override
    protected void onPause() {
        super.onPause();
        webView.onPause();
    }
}
