package com.elsha3er.mallefypdf;

import android.app.Activity;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.util.Base64;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Iterator;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {

    private WebView webView;
    private ValueCallback<Uri[]> mFilePathCallback;
    private static final int FILECHOOSER_RESULTCODE = 1001;
    private static final String CHANNEL_ID = "mallefy_downloads";
    private final ExecutorService networkExecutor = Executors.newFixedThreadPool(4);
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private long backPressedTime = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Edge-to-Edge & modern window setup
        setupEdgeToEdge();

        setContentView(R.layout.activity_main);
        createNotificationChannel();

        webView = findViewById(R.id.webview);
        setupWebView();
        webView.loadUrl("file:///android_asset/index.html");
    }

    private void setupEdgeToEdge() {
        Window window = getWindow();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            window.clearFlags(WindowManager.LayoutParams.FLAG_TRANSLUCENT_STATUS);
            window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
            window.setStatusBarColor(0xFF1E3A8A); // Deep Royal Blue
            window.setNavigationBarColor(0xFF12141A);
        }
    }

    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setAllowUniversalAccessFromFileURLs(true);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setSupportZoom(true);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);

        // Bridge exposure
        webView.addJavascriptInterface(new WebAppInterface(this), "AndroidBridge");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                if (url.startsWith("file://") || url.startsWith("https://") || url.startsWith("http://")) {
                    return false;
                }
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(intent);
                    return true;
                } catch (Exception e) {
                    return false;
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback,
                                              FileChooserParams fileChooserParams) {
                if (mFilePathCallback != null) {
                    mFilePathCallback.onReceiveValue(null);
                }
                mFilePathCallback = filePathCallback;

                Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true); // Support multi-select files!
                String[] mimetypes = {"application/pdf", "image/*", "text/*", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"};
                intent.putExtra(Intent.EXTRA_MIME_TYPES, mimetypes);

                try {
                    startActivityForResult(Intent.createChooser(intent, "اختر ملفات PDF أو صور"), FILECHOOSER_RESULTCODE);
                } catch (Exception e) {
                    mFilePathCallback = null;
                    return false;
                }
                return true;
            }
        });
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == FILECHOOSER_RESULTCODE) {
            if (mFilePathCallback == null) return;
            Uri[] results = null;
            if (resultCode == Activity.RESULT_OK && data != null) {
                if (data.getClipData() != null) {
                    int count = data.getClipData().getItemCount();
                    results = new Uri[count];
                    for (int i = 0; i < count; i++) {
                        results[i] = data.getClipData().getItemAt(i).getUri();
                    }
                } else if (data.getData() != null) {
                    results = new Uri[]{data.getData()};
                }
            }
            mFilePathCallback.onReceiveValue(results);
            mFilePathCallback = null;
        } else {
            super.onActivityResult(requestCode, resultCode, data);
        }
    }

    @Override
    public void onBackPressed() {
        if (webView == null) {
            super.onBackPressed();
            return;
        }

        // Query webapp if it wants to handle back (e.g. close open modal or return to catalog)
        webView.evaluateJavascript("typeof window.onAndroidBackPressed === 'function' ? window.onAndroidBackPressed() : false;",
                new ValueCallback<String>() {
                    @Override
                    public void onReceiveValue(String value) {
                        if ("true".equalsIgnoreCase(value) || "\"true\"".equalsIgnoreCase(value)) {
                            // Handled by JavaScript interface!
                            return;
                        }

                        if (webView.canGoBack()) {
                            webView.goBack();
                            return;
                        }

                        // Double-tap to exit confirmation
                        if (System.currentTimeMillis() - backPressedTime < 2000) {
                            MainActivity.super.onBackPressed();
                        } else {
                            backPressedTime = System.currentTimeMillis();
                            Toast.makeText(MainActivity.this, "اضغط مرة أخرى للخروج من تطبيق ملفّي", Toast.LENGTH_SHORT).show();
                        }
                    }
                });
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "تنزيلات ملفّي",
                    NotificationManager.IMPORTANCE_DEFAULT
            );
            channel.setDescription("إشعارات تنزيل ومعالجة ملفات PDF");
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }

    public class WebAppInterface {
        private final Context mContext;

        public WebAppInterface(Context c) {
            mContext = c;
        }

        @JavascriptInterface
        public void showToast(final String message) {
            mainHandler.post(new Runnable() {
                @Override
                public void run() {
                    Toast.makeText(mContext, message, Toast.LENGTH_SHORT).show();
                }
            });
        }

        /**
         * Native HTTP Engine: Executes HTTPS requests in background without WebView CORS/file restrictions.
         * Returns latency, exact HTTP status, and body/error payload.
         */
        @JavascriptInterface
        public void executeHttpRequest(final String requestId, final String urlStr, final String method,
                                       final String headersJson, final String bodyData) {
            networkExecutor.execute(new Runnable() {
                @Override
                public void run() {
                    long startTime = System.currentTimeMillis();
                    int statusCode = -1;
                    String responseBody = "";
                    String errorMessage = "";
                    boolean isSuccess = false;

                    try {
                        URL url = new URL(urlStr);
                        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                        conn.setRequestMethod(method != null ? method.toUpperCase() : "GET");
                        conn.setConnectTimeout(25000); // 25s timeout
                        conn.setReadTimeout(120000);   // 2m read timeout for AI models
                        conn.setDoInput(true);

                        // Parse headers
                        if (headersJson != null && !headersJson.isEmpty()) {
                            JSONObject headers = new JSONObject(headersJson);
                            Iterator<String> keys = headers.keys();
                            while (keys.hasNext()) {
                                String key = keys.next();
                                conn.setRequestProperty(key, headers.optString(key));
                            }
                        }

                        // Write body if POST/PUT
                        if (bodyData != null && !bodyData.isEmpty()) {
                            conn.setDoOutput(true);
                            byte[] bodyBytes = bodyData.getBytes(StandardCharsets.UTF_8);
                            try (OutputStream os = conn.getOutputStream()) {
                                os.write(bodyBytes);
                                os.flush();
                            }
                        }

                        statusCode = conn.getResponseCode();
                        long latency = System.currentTimeMillis() - startTime;

                        InputStream is = (statusCode >= 200 && statusCode < 400)
                                ? conn.getInputStream()
                                : conn.getErrorStream();

                        if (is != null) {
                            BufferedReader reader = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8));
                            StringBuilder sb = new StringBuilder();
                            String line;
                            while ((line = reader.readLine()) != null) {
                                sb.append(line).append("\n");
                            }
                            reader.close();
                            responseBody = sb.toString();
                        }

                        isSuccess = (statusCode >= 200 && statusCode < 300);

                        // Construct JSON result
                        JSONObject result = new JSONObject();
                        result.put("ok", isSuccess);
                        result.put("status", statusCode);
                        result.put("latencyMs", latency);
                        result.put("body", responseBody);
                        result.put("error", isSuccess ? "" : responseBody);

                        dispatchNativeResponse(requestId, result.toString());

                    } catch (Exception e) {
                        long latency = System.currentTimeMillis() - startTime;
                        errorMessage = e.getClass().getSimpleName() + ": " + e.getMessage();
                        try {
                            JSONObject result = new JSONObject();
                            result.put("ok", false);
                            result.put("status", statusCode > 0 ? statusCode : 0);
                            result.put("latencyMs", latency);
                            result.put("body", "");
                            result.put("error", errorMessage);
                            dispatchNativeResponse(requestId, result.toString());
                        } catch (Exception ex) {
                            ex.printStackTrace();
                        }
                    }
                }
            });
        }

        private void dispatchNativeResponse(final String requestId, final String jsonResult) {
            mainHandler.post(new Runnable() {
                @Override
                public void run() {
                    // Safe injection into window callback
                    String js = "if (window.onNativeHttpResponse) { window.onNativeHttpResponse('"
                            + escapeJs(requestId) + "', " + jsonResult + "); }";
                    webView.evaluateJavascript(js, null);
                }
            });
        }

        private String escapeJs(String input) {
            if (input == null) return "";
            return input.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n");
        }

        @JavascriptInterface
        public void saveBlobBase64(final String base64Data, final String fileName, final String mimeType) {
            try {
                byte[] pdfAsBytes = Base64.decode(base64Data, Base64.DEFAULT);
                String validMime = (mimeType != null && !mimeType.isEmpty()) ? mimeType : "application/pdf";
                String validName = (fileName != null && !fileName.isEmpty()) ? fileName : "mallefy_output.pdf";

                Uri savedUri = null;

                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    ContentValues contentValues = new ContentValues();
                    contentValues.put(MediaStore.MediaColumns.DISPLAY_NAME, validName);
                    contentValues.put(MediaStore.MediaColumns.MIME_TYPE, validMime);
                    contentValues.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);

                    Uri uri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, contentValues);
                    if (uri != null) {
                        try (OutputStream os = getContentResolver().openOutputStream(uri)) {
                            if (os != null) {
                                os.write(pdfAsBytes);
                                os.flush();
                                savedUri = uri;
                            }
                        }
                    }
                } else {
                    File downloadsDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
                    if (!downloadsDir.exists()) downloadsDir.mkdirs();
                    File outFile = new File(downloadsDir, validName);
                    try (FileOutputStream fos = new FileOutputStream(outFile)) {
                        fos.write(pdfAsBytes);
                        fos.flush();
                        savedUri = Uri.fromFile(outFile);
                    }
                }

                final String finalName = validName;
                final Uri notificationUri = savedUri;
                mainHandler.post(new Runnable() {
                    @Override
                    public void run() {
                        Toast.makeText(mContext, "✅ تم حفظ الملف في التنزيلات:\n" + finalName, Toast.LENGTH_LONG).show();
                        notifyDownloadComplete(finalName, notificationUri, validMime);
                    }
                });

            } catch (final Exception e) {
                e.printStackTrace();
                mainHandler.post(new Runnable() {
                    @Override
                    public void run() {
                        Toast.makeText(mContext, "❌ فشل حفظ الملف: " + e.getMessage(), Toast.LENGTH_LONG).show();
                    }
                });
            }
        }

        private void notifyDownloadComplete(String fileName, Uri fileUri, String mimeType) {
            try {
                NotificationManager manager = (NotificationManager) mContext.getSystemService(Context.NOTIFICATION_SERVICE);
                if (manager == null) return;

                Intent viewIntent = new Intent(Intent.ACTION_VIEW);
                viewIntent.setDataAndType(fileUri, mimeType);
                viewIntent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);

                PendingIntent pendingIntent = PendingIntent.getActivity(
                        mContext,
                        (int) System.currentTimeMillis(),
                        viewIntent,
                        Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0
                );

                android.app.Notification.Builder builder;
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    builder = new android.app.Notification.Builder(mContext, CHANNEL_ID);
                } else {
                    builder = new android.app.Notification.Builder(mContext);
                }

                android.app.Notification notification = builder
                        .setContentTitle("تم تنزيل الملف بنجاح")
                        .setContentText(fileName)
                        .setSmallIcon(R.drawable.ic_launcher)
                        .setContentIntent(pendingIntent)
                        .setAutoCancel(true)
                        .build();

                manager.notify((int) System.currentTimeMillis(), notification);
            } catch (Exception e) {
                // Ignore notification issues if restricted
            }
        }
    }
}
