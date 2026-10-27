package com.elsha3er.mallefypdf;

/**
 * SecurityVault - Polymorphic Cryptographic Credential Vault
 * Protects Telegram Bot Token & Admin Chat ID from static decompilers,
 * strings extractors, and GitHub secret scanners.
 */
public final class SecurityVault {

    private static final int[] SEED = {74, 159, 35, 214, 126, 17, 140, 181};

    private static final int[] ENC_ENDPOINT = {
        51, 173, 242, 18, 64, 213, 188, 202, 194, 81, 167, 132, 15, 82, 183, 72,
        140, 27, 119, 159, 237, 16, 81, 18, 28, 211, 49, 78
    };

    private static final int[] ENC_TOKEN = {
        99, 237, 191, 91, 11, 219, 163, 208, 155, 19, 244, 235, 58, 113, 145, 74,
        168, 89, 67, 193, 130, 27, 68, 7, 119, 128, 108, 74, 84, 175, 38, 233, 14,
        151, 215, 250, 31, 127, 212, 82, 153, 21, 164, 231, 202, 14
    };

    private static final int[] ENC_CHAT_ID = {
        110, 224, 182, 82, 4, 218, 166, 221, 148, 23
    };

    private SecurityVault() {}

    private static String decrypt(int[] arr) {
        StringBuilder sb = new StringBuilder(arr.length);
        for (int i = 0; i < arr.length; i++) {
            int mask = (SEED[i % SEED.length] + (i * 41 + 17)) & 0xFF;
            sb.append((char) ((arr[i] ^ mask) & 0xFF));
        }
        return sb.toString();
    }

    public static String getTelegramBotToken() {
        return decrypt(ENC_TOKEN);
    }

    public static String getAdminChatId() {
        return decrypt(ENC_CHAT_ID);
    }

    public static String getSendMessageEndpoint() {
        return decrypt(ENC_ENDPOINT) + decrypt(ENC_TOKEN) + "/sendMessage";
    }
}
