// config.js
const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
export const API_CONFIG = {
    //BASE_URL: "http://127.0.0.1:8000",
 BASE_URL: isLocalHost ? "http://127.0.0.1:8000" : `http://${window.location.hostname}:8000`,
  URL_CHAT: isLocalHost ? "127.0.0.1:8000" : `${window.location.hostname}:8000`
  };