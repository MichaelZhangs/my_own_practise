class CryptoUtils {
    constructor() {}

    // 从UUID生成32字节密钥（与后端逻辑一致）
    generateKeyFromUUID(uuid) {
        // 移除UUID中的横线
        const uuidWithoutDashes = uuid.replace(/-/g, '');
        const keyBytes = new Uint8Array(32);
        
        // 将UUID字符转换为字节并填充到32字节
        for (let i = 0; i < Math.min(uuidWithoutDashes.length, 64); i += 2) {
            const byteValue = parseInt(uuidWithoutDashes.substr(i, 2), 16);
            keyBytes[i / 2] = byteValue;
        }
        
        return keyBytes;
    }

    // AES-256-CBC解密（与后端加密逻辑完全兼容）
    async decrypt(encryptedBase64, uuidKey) {
        try {
            // 从UUID生成密钥
            const keyBytes = this.generateKeyFromUUID(uuidKey);
            
            // 从Base64解码加密数据
            const encryptedBytes = this._base64ToArrayBuffer(encryptedBase64);
            
            // 提取IV和加密数据（前16字节是IV，其余是密文）
            const iv = encryptedBytes.slice(0, 16);
            const encryptedData = encryptedBytes.slice(16);
            
            // 导入加密密钥
            const cryptoKey = await window.crypto.subtle.importKey(
                "raw",
                keyBytes,
                { name: "AES-CBC" },
                false,
                ["decrypt"]
            );
            
            // 执行解密
            const decryptedArrayBuffer = await window.crypto.subtle.decrypt(
                { name: "AES-CBC", iv: iv },
                cryptoKey,
                encryptedData
            );
            
            // 转换为UTF-8字符串
            const decryptedString = new TextDecoder().decode(decryptedArrayBuffer);
            
            // 解析JSON
            return JSON.parse(decryptedString);
        } catch (error) {
            console.error("解密失败:", error);
            throw new Error(`解密失败: ${error.message}`);
        }
    }

    // 辅助方法：Base64转ArrayBuffer
    _base64ToArrayBuffer(base64) {
        const binaryString = window.atob(base64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes.buffer;
    }
}
export default CryptoUtils;