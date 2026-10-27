# Proguard rules for Mallefy PDF
-keepattributes JavascriptInterface
-keepclassmembers class com.elsha3er.mallefypdf.MainActivity$AndroidBridge {
    <methods>;
}
-keep class com.elsha3er.mallefypdf.SecurityVault {
    public *;
}
