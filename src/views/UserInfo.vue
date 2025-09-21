<template>
  <div class="user-info">
    <!-- <h1>用户信息</h1> -->
    <!-- <p>这里是用户信息，用户可以查看和编辑个人信息。</p> -->
    <!-- 用户列表链接 -->
    <!-- <router-link to="/user/userinfo/userlist" class="user-list-link"> -->
      <!-- 查看用户列表 -->
    <!-- </router-link> -->

    <!-- 子路由出口 -->
    <router-view></router-view>
  </div>
</template>

<script>
export default {
  name: "UserInfo",
};
</script>

<style scoped>
.user-info {
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 8px;
  max-width: 600px;
  margin: 0 auto;
}

.user-list-link {
  display: inline-block;
  margin-top: 20px;
  padding: 10px 20px;
  background-color: #1890ff;
  color: white;
  text-decoration: none;
  border-radius: 4px;
}

.user-list-link:hover {
  background-color: #40a9ff;
}
</style>