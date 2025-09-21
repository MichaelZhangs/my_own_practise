import axios from 'axios'
import { useStore } from 'vuex'
import { computed } from 'vue'
import { API_CONFIG } from '@/config/config'
import { ElMessage } from 'element-plus'



export default function useComment() {
  const currentUser = computed(() => store.state.user || {})
  const store = useStore()


  const postComment = async (moment) => {
    if (!moment.commentInput.trim()) return

  try {
    const response = await axios.post(
      `${API_CONFIG.BASE_URL}/article/post_comment`,
      {
        moment_id: moment.id,
        comment: moment.commentInput,
        comment_user_name: currentUser.value.username,
        comment_user_id: currentUser.value.id
      },
      { headers: { Authorization: `Bearer ${store.state.token}` } }
    )

    if (response.data.success) {
      // 在数组开头添加新评论
      moment.comments.unshift({
        id: response.data.id,
        comment: moment.commentInput,
        created_at: new Date().toISOString(),
        comment_user_name: currentUser.value.username,
        comment_user_photo: currentUser.value.photo,
        likes: 0,
        isLiked: false,
        replies: []
      })
      
      // 更新评论数量
      moment.stats.comments += 1
      
      // 清空输入框并关闭
      moment.commentInput = ''
      moment.showCommentInput = false
      
      ElMessage.success('评论发布成功')
    }
  } catch (error) {
    console.error('评论失败:', error)
    ElMessage.error('评论发布失败')
  }
}

  const postReply = async (commentId, content, userInfo) => {
    if (!content.trim()) return null

    try {
      const response = await axios.post(
        `${API_CONFIG.BASE_URL}/article/post_reply`,
        {
          parent_comment_id: commentId,
          comment: content,
          comment_user_id: userInfo.id
        }
      )

      if (response.data.success) {
        ElMessage.success('回复成功')
        return {
          ...response.data.reply,
          comment_user_name: userInfo.username,
          comment_user_photo: userInfo.photo
        }
      }
      return null
    } catch (error) {
      ElMessage.error('回复失败')
      return null
    }
  }

  return {
    postComment,
    postReply
  }
}