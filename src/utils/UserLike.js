import { useStore } from 'vuex'
import {  computed } from 'vue'
import axios from 'axios'
import { API_CONFIG } from '@/config/config'
import { ElMessage } from 'element-plus'

export default function useLike() {
  const store = useStore()

  const currentUser = computed(() => store.state.user || {})

  // 修复参数顺序和逻辑
  const toggleLike = async (momentsData,resourceType, resourceId) => {
    const urlMap = {
      'moment': `${API_CONFIG.BASE_URL}/article/like_moment`,
      'comment': `${API_CONFIG.BASE_URL}/article/like_comment`
    }
    console.log("resourceType_1: ", resourceType)
    console.log("momentsData: ", momentsData)
    console.log("resourceId - 1: ", resourceId)
   

   let targetResource
   if (resourceType === 'moment') {
     targetResource = momentsData.find(moment => 
       moment.id === resourceId || moment.id.toString() === resourceId.toString()
     )
   } else if (resourceType === 'comment') {
     for (const moment of momentsData) {
       if (!moment.comments) continue
       
       targetResource = moment.comments.find(comment => 
         comment.id === resourceId || comment.id.toString() === resourceId.toString()
       )
       
       if (targetResource) break
     }
   }
    
   if (!targetResource) {
    console.error(`未找到${resourceType}资源:`, resourceId)
    console.log('当前所有动态ID:', momentsData.map(m => m.id))
    ElMessage.error(`找不到要操作的${resourceType === 'moment' ? '动态' : '评论'}`)
    return null
  }

    // 保存原始状态用于回滚
    const originalIsLiked = targetResource.isLiked
    const originalLikes = targetResource.stats?.likes || 0
    
    try {
      // 立即更新UI状态
      targetResource.isLiked = !targetResource.isLiked
      
      // 初始化stats对象（如果不存在）
      if (!targetResource.stats) {
        targetResource.stats = { likes: 0 }
      }
      
      targetResource.stats.likes += targetResource.isLiked ? 1 : -1

      const response = await axios.post(urlMap[resourceType], {
        [resourceType === 'moment' ? 'moment_id' : 'comment_id']: resourceId,
        user_id: currentUser.value.id,
        is_like: targetResource.isLiked
      }, {
        headers: {
          Authorization: `Bearer ${store.state.token}`
        },
        timeout: 5000
      })

      if (response.data.msg) {
        // 更新前端状态，确保与后端数据一致
        targetResource.isLiked = response.data.is_liked
        targetResource.stats.likes = response.data.likes_count
        
        // 更新like_users列表
        if (response.data.is_liked) {
          targetResource.like_users = [
            ...(targetResource.like_users || []),
            currentUser.value.id
          ]
        } else {
          targetResource.like_users = (targetResource.like_users || [])
            .filter(id => id !== currentUser.value.id)
        }
        
        ElMessage.success(targetResource.isLiked ? '点赞成功' : '已取消点赞')
        
        // 返回关键数据给调用者
        return {
          isLiked: targetResource.isLiked,
          likes: targetResource.stats.likes
        }
      } else {
        throw new Error(response.data.msg || '操作失败')
      }
    } catch (error) {
      // 回滚状态
      targetResource.isLiked = originalIsLiked
      targetResource.stats.likes = originalLikes
      
      console.error('点赞操作失败:', error)
      ElMessage.error(`操作失败: ${error.response?.data?.msg || '网络错误'}`)
      
      // 返回null表示操作失败
      return null
    }
  }

  return {
    toggleLike
  }
}
