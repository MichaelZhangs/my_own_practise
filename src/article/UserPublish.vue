<template>
  <div class="publish-container">
    <!-- 编辑器工具栏 -->
    <div class="editor-toolbar relative">
      <button @click="formatText('bold')" title="加粗">
        <strong>B</strong>
      </button>
      <button @click="formatText('italic')" title="斜体">
        <em>I</em>
      </button>
      <button @click="formatText('underline')" title="下划线">
        <u>U</u>
      </button>
      <!-- 添加表情按钮 -->
      <button 
        @click="toggleEmojiPicker" 
        title="插入表情" 
        class="relative z-10"
        aria-label="插入表情"
        aria-expanded="showEmojiPicker"
        aria-haspopup="true"
      >
        😀
      </button>
   
      <!-- 表情选择面板 -->
      <div 
        v-if="showEmojiPicker" 
        class="emoji-picker absolute"
        role="menu"
        aria-labelledby="emoji-button"
      >
        <div 
          v-for="(emoji, index) in emojiList"
          :key="index"
          class="emoji-item"
          @click="insertEmoji(emoji)"
          role="menuitem"
          tabindex="0"
        >
          {{ emoji }}
        </div>
      </div>
    </div>
    
    <!-- 内容编辑器 -->
    <div 
      ref="editor" 
      contenteditable="true"
      class="content-editor"
      placeholder="分享新鲜事..."
      @input="updateContent"
      @click="showEmojiPicker = false"
      aria-label="内容编辑器"
    ></div>
    
    <!-- 上传区域 -->
    <div class="media-upload-section">
      <input 
        type="file" 
        ref="fileInput" 
        accept="image/*,video/*" 
        style="display: none" 
        @change="handleFileSelect"
        multiple
        aria-label="选择文件上传"
      >
      <div 
        class="upload-card" 
        @click="triggerFileInput"
        @dragover.prevent="dragOver = true"
        @dragleave="dragOver = false"
        @drop.prevent="handleDrop"
        :class="{ 'drag-over': dragOver }"
      >
        <el-icon class="upload-icon"><Upload /></el-icon>
        <div class="upload-text">
          <p>点击或拖拽文件到此处</p>
          <p class="hint-text">支持图片和视频 (最大 2G)</p>
        </div>
      </div>
      
      <!-- 上传进度 -->
      <div v-if="uploadProgress > 0" class="upload-progress">
        <el-progress 
          :percentage="uploadProgress" 
          :stroke-width="12"
          :status="uploadStatus"
        />
        <span class="progress-text">
          {{ uploadStatus === 'success' ? '上传完成' : 
             uploadStatus === 'exception' ? '上传失败' : 
             `上传中 ${uploadProgress}%` }}
        </span>
      </div>
      
      <!-- 预览区域 -->
      <div class="media-preview-grid">
        <div 
          v-for="(file, index) in mediaFiles" 
          :key="file.id"
          class="media-preview-item"
          :class="[`media-${file.type}`, { 'upload-failed': file.status === 'error' }]"
        >
          <div class="media-content">
            <img 
              v-if="file.type === 'image'" 
              :src="file.previewUrl" 
              alt="预览图"
            />
            <video 
              v-else 
              :src="file.previewUrl"
              controls
              muted
            ></video>
          </div>
          
          <div class="media-info">
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formatFileSize(file.size) }}</span>
          </div>
          
          <div class="media-actions">
            <el-icon 
              v-if="file.status === 'error'" 
              class="retry-icon"
              @click="retryUpload(index)"
            ><Refresh /></el-icon>
            
            <el-icon 
              class="remove-icon"
              @click="removeFile(index)"
            ><Close /></el-icon>
          </div>
          
          <div v-if="file.status === 'uploading'" class="upload-progress-bar">
            <div 
              class="progress-fill" 
              :style="{ width: `${file.progress}%` }"
            ></div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 发布按钮 -->
    <div class="publish-actions">
      <el-button 
          type="primary" 
          :loading="isPublishing"
          :disabled="!canPublish"
          @click="handlePublish"
          class="publish-button"
          :class="canPublish ? 'publish-enabled' : 'publish-disabled'"
          style="margin-right: 10px;"
        >
          {{ isPublishing ? '发布中...' : '发布' }}
            </el-button>
            <el-button 
              type="text" 
              @click="handleCancel"
              class="cancel-button"
            >
              取消
            </el-button>
    </div>
  </div>
</template>

<script>
import { ref, computed, nextTick, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { Upload, Close, Refresh } from '@element-plus/icons-vue'
import { API_CONFIG } from '@/config/config'
import { useStore } from 'vuex'
import { useRouter } from 'vue-router'
// 增加表情数据
import emojis from '@/utils/emojis'

export default {
  name: 'PublishPage',
  components: {
    Upload,
    Close,
    Refresh
  },
  setup() {
    // 编辑器相关
    const editor = ref(null)
    const content = ref('')
    const store = useStore()
    const router = useRouter()
    // 新增表情相关状态
    const showEmojiPicker = ref(false)
    const emojiList = ref([]) // 初始化空数组
    
    // 验证emojis导入是否正确
    onMounted(() => {
      try {
        // 尝试加载emojis
        if (Array.isArray(emojis) && emojis.length > 0) {
          emojiList.value = emojis
          console.log('表情加载成功，共加载', emojis.length, '个表情')
        } else {
          console.error('表情数据格式不正确，应为数组')
          // 设置默认表情
          emojiList.value = ['😀', '😃', '😄', '😁', '😆', '😅', '😂', '🤣']
        }
      } catch (error) {
        console.error('加载表情失败:', error)
        // 设置默认表情
        emojiList.value = ['😀', '😃', '😄', '😁', '😆', '😅', '😂', '🤣']
      }
    })

    // 表情面板切换
    const toggleEmojiPicker = () => {
      showEmojiPicker.value = !showEmojiPicker.value
      
      // 确保编辑器获取焦点
      if (showEmojiPicker.value) {
        nextTick(() => {
          editor.value.focus()
          console.log('编辑器已获取焦点')
        })
      }
    }

// 插入表情到内容末尾
const insertEmoji = (emoji) => {
  console.log('尝试插入表情:', emoji)
  
  // 确保编辑器有焦点
  if (!document.activeElement.isSameNode(editor.value)) {
    editor.value.focus()
    console.log('已重新获取编辑器焦点')
  }
  
  try {
    // 创建包含表情的span元素
    const emojiSpan = document.createElement('span')
    emojiSpan.textContent = emoji
    emojiSpan.className = 'emoji-inline'
    
    // 如果编辑器为空，直接添加表情
    if (editor.value.innerHTML.trim() === '') {
      editor.value.appendChild(emojiSpan)
    } else {
      // 找到最后一个子节点
      const lastChild = editor.value.lastChild
      
      // 如果最后一个子节点是BR标签，将表情插入到BR前面
      if (lastChild && lastChild.tagName === 'BR') {
        editor.value.insertBefore(emojiSpan, lastChild)
      } else {
        // 否则将表情添加到最后
        editor.value.appendChild(emojiSpan)
      }
    }
    
    // 更新内容
    content.value = editor.value.innerHTML
    
    // 触发input事件
    const event = new Event('input', { bubbles: true })
    editor.value.dispatchEvent(event)
    
    // 将光标定位到表情后面
    setCaretAfter(emojiSpan)
    
    console.log('表情插入成功')
  } catch (error) {
    console.error('插入表情失败:', error)
    ElMessage.error('插入表情失败，请重试')
  } finally {
    showEmojiPicker.value = false
  }
}

// 设置光标位置到指定元素后面
const setCaretAfter = (element) => {
  const range = document.createRange()
  const selection = window.getSelection()
  
  range.setStartAfter(element)
  range.collapse(true)
  
  selection.removeAllRanges()
  selection.addRange(range)
  
  // 确保编辑器滚动到可见位置
  element.scrollIntoView(false)
}

    // 上传相关
    const fileInput = ref(null)
    const mediaFiles = ref([])
    const dragOver = ref(false)
    const uploadProgress = ref(0)
    const uploadStatus = ref('')
    const isPublishing = ref(false)
    
    // 格式工具
    const formatText = (command) => {
      document.execCommand(command, false)
      editor.value.focus()
    }
    
    const updateContent = (e) => {
      content.value = e.target.innerHTML
    }

    // 文件处理
    const triggerFileInput = () => {
      fileInput.value.click()
    }
    
    const handleFileSelect = async (e) => {
      const files = Array.from(e.target.files)
      await processFiles(files)
      e.target.value = '' // 重置input
    }
    
    const handleDrop = async (e) => {
      dragOver.value = false
      const files = Array.from(e.dataTransfer.files)
      await processFiles(files)
    }
    
    const processFiles = async (files) => {
      for (const file of files) {
        // 验证文件类型和大小
        if (!file.type.startsWith('image/') && !file.type.startsWith('video/') && !file.type.startsWith('audio/')) {
          // ElMessage.warning(`文件 ${file.name} 不是支持的图片或视频类型`)
          continue
        }
        
        if (file.size > 2000 * 1024 * 1024) { // 2000MB限制
          // ElMessage.warning(`文件 ${file.name} 超过2G大小限制`)
          continue
        }
        
        // 生成预览URL
        const previewUrl = URL.createObjectURL(file)
        const fileType = file.type.split('/')[0]
        
        // 添加到媒体文件列表
        const fileId = Date.now() + Math.random().toString(36).substr(2, 9)
        mediaFiles.value.push({
          id: fileId,
          raw: file,
          previewUrl,
          type: fileType,
          name: file.name,
          size: file.size,
          status: 'pending',
          progress: 0,
          serverUrl: null
        })
        
        // 开始上传
        await uploadFile(fileId)
      }
    }
    
    const uploadFile = async (fileId) => {
      const fileIndex = mediaFiles.value.findIndex(f => f.id === fileId)
      if (fileIndex === -1) return
      
      const fileObj = mediaFiles.value[fileIndex]
      fileObj.status = 'uploading'
      
      try {
        const formData = new FormData()
        formData.append('file', fileObj.raw)
        
        const response = await axios.post(`${API_CONFIG.BASE_URL}/article/upload/media`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            const progress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            )
            fileObj.progress = progress
            uploadProgress.value = progress
          }
        })
        
        fileObj.status = 'success'
        fileObj.serverUrl = response.data.url
        uploadStatus.value = 'success'
        
      } catch (error) {
        console.error('上传失败:', error)
        fileObj.status = 'error'
        uploadStatus.value = 'exception'
        ElMessage.error(`上传 ${fileObj.name} 失败: ${error.message}`)
      }
    }
    
    const retryUpload = (index) => {
      const fileId = mediaFiles.value[index].id
      mediaFiles.value[index].status = 'pending'
      uploadFile(fileId)
    }
    
    const removeFile = (index) => {
      const file = mediaFiles.value[index]
      URL.revokeObjectURL(file.previewUrl)
      mediaFiles.value.splice(index, 1)
      
      if (mediaFiles.value.length === 0) {
        uploadProgress.value = 0
        uploadStatus.value = ''
      }
    }
    
    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    // 发布相关
    const canPublish = computed(() => {
      const hasContent = content.value.trim().length > 0
      const hasMedia = mediaFiles.value.some(f => f.status === 'success')
      return (hasContent || hasMedia) && 
             !mediaFiles.value.some(f => f.status === 'uploading')
    })
    
    const handlePublish = async () => {
      if (!canPublish.value || isPublishing.value) return
      
      isPublishing.value = true
      
      try {
        const postData = {
          content: content.value,
          user_id: store.state.user.id,
          media: mediaFiles.value
            .filter(f => f.status === 'success')
            .map(f => ({
              url: f.serverUrl,
              type: f.type
            }))
        }
        
        const response = await axios.post(
        `${API_CONFIG.BASE_URL}/article/moments`, 
        postData,
        {
          headers: {
            'Authorization': `Bearer ${store.state.token}`,
            'Content-Type': 'application/json' // 修改为JSON格式
          }
        }
      )
        // console.log("response data, ", response.data)
        if (response.data.status_code) {
          // ElMessage.success('发布成功')
          // 清空内容
          content.value = ''
          editor.value.innerHTML = ''
          mediaFiles.value = []
        // 添加路由跳转
        router.push('/moments').then(() => {
            // 重新加载页面
            window.location.reload();
          });
        }
      } catch (error) {
        ElMessage.error(`发布失败: ${error.message}`)
      } finally {
        isPublishing.value = false
      }
    }

    const handleCancel = () => {
      router.push('/moments')
    }
    
    return {
      // 新增返回的属性
      showEmojiPicker,
      emojiList,
      toggleEmojiPicker,
      insertEmoji,
      editor,
      content,
      fileInput,
      mediaFiles,
      dragOver,
      uploadProgress,
      uploadStatus,
      isPublishing,
      canPublish,
      formatText,
      updateContent,
      triggerFileInput,
      handleFileSelect,
      handleDrop,
      removeFile,
      retryUpload,
      formatFileSize,
      handlePublish,
      handleCancel
    }
  }
}
</script>

<style scoped>
/* 新增表情相关样式 */
.emoji-picker {
  position: absolute;
  top: 40px;
  left: 0;
  width: 300px;
  max-height: 200px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 10px;
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 5px;
  overflow-y: auto;
  z-index: 1000;
  transition: opacity 0.2s ease-in-out;
}

.emoji-item {
  cursor: pointer;
  font-size: 20px;
  padding: 5px;
  text-align: center;
  transition: all 0.2s;
  border-radius: 4px;
}

.emoji-item:hover {
  background: #f0f0f0;
  transform: scale(1.2);
}

.emoji-inline {
  display: inline-block;
  font-size: inherit;
  line-height: 1;
  vertical-align: -0.125em;
}

/* 调整工具栏按钮样式 */
.editor-toolbar {
  position: relative; /* 为表情面板定位 */
  display: flex;
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px solid #eee;
}

.editor-toolbar button {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.editor-toolbar button:hover {
  background: #f0f0f0;
}

.publish-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.content-editor {
  min-height: 200px;
  padding: 15px;
  margin: 15px 0;
  border: 1px solid #eee;
  border-radius: 4px;
  outline: none;
  font-size: 16px;
  line-height: 1.6;
}

.content-editor:empty::before {
  content: attr(placeholder);
  color: #999;
}

.media-upload-section {
  margin-top: 20px;
}

.upload-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px;
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  background-color: #f8f9fa;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-card.drag-over {
  border-color: #409eff;
  background-color: #f0f7ff;
}

.upload-icon {
  font-size: 48px;
  color: #8c939d;
  margin-bottom: 10px;
}

.upload-text {
  text-align: center;
  color: #606266;
}

.hint-text {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.upload-progress {
  margin-top: 15px;
}

.progress-text {
  display: block;
  text-align: center;
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.media-preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 15px;
  margin-top: 20px;
}

.media-preview-item {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s;
}

.media-preview-item:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.media-preview-item.upload-failed {
  border: 1px solid #f56c6c;
}

.media-content {
  width: 100%;
  height: 150px;
  overflow: hidden;
}

.media-content img,
.media-content video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.media-info {
  padding: 8px;
  background: #fff;
}

.file-name {
  display: block;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-size {
  display: block;
  font-size: 11px;
  color: #909399;
}

.media-actions {
  position: absolute;
  top: 5px;
  right: 5px;
  display: flex;
  gap: 5px;
}

.remove-icon,
.retry-icon {
  background: rgba(0, 0, 0, 0.7);
  color: white;
  border-radius: 50%;
  padding: 4px;
  cursor: pointer;
  font-size: 12px;
}

.retry-icon {
  background: rgba(255, 255, 255, 0.9);
  color: #409eff;
}

.upload-progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: rgba(0, 0, 0, 0.1);
}

.progress-fill {
  height: 100%;
  background: #409eff;
  transition: width 0.3s;
}

.publish-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #eee;
}

/* 发布按钮样式 */
.publish-button {
  transition: all 0.2s ease;
  border-radius: 20px !important;
  padding: 10px 28px !important;
}
.publish-button.publish-enabled {
  background-color: #4CD964 !important;
  border-color: #4CD964 !important;
  color: white !important;
}

.publish-button.publish-enabled:hover {
  background-color: #3BC453 !important;
  border-color: #3BC453 !important;
  box-shadow: 0 2px 6px rgba(76, 217, 100, 0.3);
}

.publish-button.publish-disabled {
  background-color: #EDF2F7 !important;
  border-color: #E2E8F0 !important;
  color: #A0AEC0 !important;
  cursor: not-allowed;
}
/* 取消按钮样式 */
.cancel-button {
  border-radius: 20px !important;
  padding: 10px 28px !important;
  color: #909399 !important;
  border: 1px solid #DCDFE6 !important;
  background-color: #FFFFFF !important;
  transition: all 0.2s ease;
}

.cancel-button:hover {
  color: #4CD964 !important;
  border-color: #4CD964 !important;
  background-color: rgba(76, 217, 100, 0.05) !important;
}

.cancel-button:active {
  transform: scale(0.98);
}

/* 调整取消按钮样式保持统一 */
.el-button[type="text"] {
  color: #718096;
  border: 1px solid #E2E8F0;
}

.el-button[type="text"]:hover {
  color: #4CD964;
  border-color: #4CD964;
  background-color: rgba(76, 217, 100, 0.1);
}


.el-button[type="text"] {
  color: #409eff; /* 取消按钮文字颜色 */
  padding: 10px 16px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  transition: all 0.2s;
}

.el-button[type="text"]:hover {
  background-color: #f4f7fc;
  border-color: #c6d1e3;
}
</style>  

