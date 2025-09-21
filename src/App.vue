<template>
  <div id="app">
    <router-view></router-view>
    <!-- <img alt="Vue logo" src="./assets/logo.png"> -->
    <HelloWorld msg="Welcome"/>
    <UserLogin />

  </div>
</template>

<script>


// import UserLogin from "./components/UserLogin.vue";

export default {
  components: {
    // UserLogin,

  },
};
</script>

<style>
/* 全局样式 */
body {
  margin: 0;
  font-family: Arial, sans-serif;
  background-color: #f0f2f5; /* 背景颜色 */
}
</style>