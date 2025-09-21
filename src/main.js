import { createApp } from "vue";
import App from "./App.vue";
import router from "./router"; // 导入路由配置
// import store from './store'; // 引入 Vuex Store
import store from "./store";

createApp(App)
        .use(router)
        .use(store) // 使用路由
        .mount("#app");