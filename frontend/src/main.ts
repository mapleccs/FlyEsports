import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'

// 正确配置dayjs以支持Ant Design Vue的DatePicker
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import localeData from 'dayjs/plugin/localeData'
import weekday from 'dayjs/plugin/weekday'
import weekOfYear from 'dayjs/plugin/weekOfYear'
import weekYear from 'dayjs/plugin/weekYear'
import dayOfYear from 'dayjs/plugin/dayOfYear'
import customParseFormat from 'dayjs/plugin/customParseFormat'
import advancedFormat from 'dayjs/plugin/advancedFormat'
import relativeTime from 'dayjs/plugin/relativeTime'

// 扩展dayjs插件
dayjs.extend(localeData)
dayjs.extend(weekday)
dayjs.extend(weekOfYear)
dayjs.extend(weekYear)
dayjs.extend(dayOfYear)
dayjs.extend(customParseFormat)
dayjs.extend(advancedFormat)
dayjs.extend(relativeTime)

// 设置默认语言为中文
dayjs.locale('zh-cn')

// 导入原生Date工具函数作为补充
import dateUtils from '@/utils/dateUtils'

console.log('Dayjs配置完成，支持Ant Design Vue DatePicker')

import App from './App.vue'
import router from './router'
import { vPermission, vRole, vCan, vAdmin, vAuth } from '@/shared/directives/permission'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(Antd)

// 注册权限指令
app.directive('permission', vPermission)
app.directive('role', vRole)
app.directive('can', vCan)
app.directive('admin', vAdmin)
app.directive('auth', vAuth)

// 全局配置dayjs
app.config.globalProperties.$dayjs = dayjs

// 先mount应用，再初始化认证状态
app.mount('#app')
