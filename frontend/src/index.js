import React from 'react';
import ReactDOM from 'react-dom/client'; // 从 'react-dom/client' 引入 createRoot
import App from './App.jsx';
import 'antd/dist/reset.css'; // 如果使用 Ant Design 5.x 样式
import { notification } from 'antd'; // 强制覆盖Antd通知框样式


// 获取 root 节点
const rootElement = document.getElementById('root');

// 使用 createRoot 进行渲染
const root = ReactDOM.createRoot(rootElement);


notification.config({
  placement: 'topRight',
  top: 24,
  duration: 3,
});

const globalStyles = `  .ant-notification-notice { width: auto !important; max-width: 800px; }
  .ant-notification-notice-description { padding:0 !important; }`;

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);