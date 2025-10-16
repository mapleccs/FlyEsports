/**
 * 原生Date工具函数 - 替代dayjs避免第三方库兼容性问题
 *
 * 提供与dayjs相似的API，但基于原生JavaScript Date对象
 * 完全兼容Ant Design Vue，无需担心第三方库冲突
 */

export interface DateInstance {
  format(pattern: string): string
  add(
    value: number,
    unit: 'day' | 'hour' | 'minute' | 'second' | 'week' | 'month' | 'year'
  ): DateInstance
  isBefore(other: DateInstance | Date | string | number): boolean
  isAfter(other: DateInstance | Date | string | number): boolean
  startOf(unit: 'day' | 'hour' | 'minute' | 'second' | 'week' | 'month' | 'year'): DateInstance
  diff(other: DateInstance | Date | string | number, unit: 'hour' | 'day' | 'minute'): number
  toISOString(): string
  isValid(): boolean
  valueOf(): number
}

class NativeDate implements DateInstance {
  private date: Date

  constructor(input?: Date | string | number) {
    if (!input) {
      this.date = new Date()
    } else if (input instanceof Date) {
      this.date = new Date(input)
    } else {
      this.date = new Date(input)
    }
  }

  format(pattern: string): string {
    const year = this.date.getFullYear()
    const month = this.date.getMonth() + 1
    const day = this.date.getDate()
    const hour = this.date.getHours()
    const minute = this.date.getMinutes()
    const second = this.date.getSeconds()

    return pattern
      .replace(/YYYY/g, year.toString())
      .replace(/MM/g, month.toString().padStart(2, '0'))
      .replace(/DD/g, day.toString().padStart(2, '0'))
      .replace(/HH/g, hour.toString().padStart(2, '0'))
      .replace(/mm/g, minute.toString().padStart(2, '0'))
      .replace(/ss/g, second.toString().padStart(2, '0'))
      .replace(/M月/g, `${month}月`)
      .replace(/D日/g, `${day}日`)
      .replace(/年/g, '年')
      .replace(/月/g, '月')
      .replace(/日/g, '日')
  }

  add(
    value: number,
    unit: 'day' | 'hour' | 'minute' | 'second' | 'week' | 'month' | 'year'
  ): DateInstance {
    const newDate = new Date(this.date)

    switch (unit) {
      case 'second':
        newDate.setSeconds(newDate.getSeconds() + value)
        break
      case 'minute':
        newDate.setMinutes(newDate.getMinutes() + value)
        break
      case 'hour':
        newDate.setHours(newDate.getHours() + value)
        break
      case 'day':
        newDate.setDate(newDate.getDate() + value)
        break
      case 'week':
        newDate.setDate(newDate.getDate() + value * 7)
        break
      case 'month':
        newDate.setMonth(newDate.getMonth() + value)
        break
      case 'year':
        newDate.setFullYear(newDate.getFullYear() + value)
        break
    }

    return new NativeDate(newDate)
  }

  isBefore(other: DateInstance | Date | string | number): boolean {
    const otherDate = this.parseDate(other)
    return this.date.getTime() < otherDate.getTime()
  }

  isAfter(other: DateInstance | Date | string | number): boolean {
    const otherDate = this.parseDate(other)
    return this.date.getTime() > otherDate.getTime()
  }

  startOf(unit: 'day' | 'hour' | 'minute' | 'second' | 'week' | 'month' | 'year'): DateInstance {
    const newDate = new Date(this.date)

    switch (unit) {
      case 'second':
        newDate.setMilliseconds(0)
        break
      case 'minute':
        newDate.setSeconds(0, 0)
        break
      case 'hour':
        newDate.setMinutes(0, 0, 0)
        break
      case 'day':
        newDate.setHours(0, 0, 0, 0)
        break
      case 'week': {
        const dayOfWeek = newDate.getDay()
        const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
        newDate.setDate(newDate.getDate() + mondayOffset)
        newDate.setHours(0, 0, 0, 0)
        break
      }
      case 'month':
        newDate.setDate(1)
        newDate.setHours(0, 0, 0, 0)
        break
      case 'year':
        newDate.setMonth(0, 1)
        newDate.setHours(0, 0, 0, 0)
        break
    }

    return new NativeDate(newDate)
  }

  diff(other: DateInstance | Date | string | number, unit: 'hour' | 'day' | 'minute'): number {
    const otherDate = this.parseDate(other)
    const diffMs = this.date.getTime() - otherDate.getTime()

    switch (unit) {
      case 'minute':
        return Math.floor(diffMs / (1000 * 60))
      case 'hour':
        return Math.floor(diffMs / (1000 * 60 * 60))
      case 'day':
        return Math.floor(diffMs / (1000 * 60 * 60 * 24))
      default:
        return diffMs
    }
  }

  toISOString(): string {
    return this.date.toISOString()
  }

  isValid(): boolean {
    return !isNaN(this.date.getTime())
  }

  valueOf(): number {
    return this.date.getTime()
  }

  private parseDate(input: DateInstance | Date | string | number): Date {
    if (input instanceof NativeDate) {
      return new Date(input.date)
    } else if (input instanceof Date) {
      return new Date(input)
    } else if (typeof input === 'number') {
      return new Date(input)
    } else if (typeof input === 'string') {
      return new Date(input)
    } else {
      // 如果是其他类型的DateInstance，获取其数值
      return new Date((input as DateInstance).valueOf())
    }
  }
}

// 主要的日期工具函数 - 替代dayjs()
export function dateUtils(input?: Date | string | number): DateInstance {
  return new NativeDate(input)
}

// 常用的静态方法
dateUtils.format = (date: Date | string | number, pattern: string): string => {
  return new NativeDate(date).format(pattern)
}

dateUtils.isValid = (date: Date | string | number): boolean => {
  return new NativeDate(date).isValid()
}

dateUtils.now = (): DateInstance => {
  return new NativeDate()
}

// 为了兼容现有代码，提供一些dayjs常用的功能
export const formatDate = (
  date: Date | string | number,
  pattern: string = 'YYYY-MM-DD HH:mm:ss'
): string => {
  return dateUtils(date).format(pattern)
}

export const addTime = (
  date: Date | string | number,
  value: number,
  unit: 'day' | 'hour' | 'minute' | 'second' | 'week' | 'month' | 'year'
): DateInstance => {
  return dateUtils(date).add(value, unit)
}

export const isBefore = (date1: Date | string | number, date2: Date | string | number): boolean => {
  return dateUtils(date1).isBefore(dateUtils(date2))
}

export const isAfter = (date1: Date | string | number, date2: Date | string | number): boolean => {
  return dateUtils(date1).isAfter(dateUtils(date2))
}

export const calculateDuration = (
  startDate: Date | string | number,
  endDate: Date | string | number
): string => {
  const start = dateUtils(startDate)
  const end = dateUtils(endDate)

  if (!start.isValid() || !end.isValid()) {
    return ''
  }

  const hours = end.diff(start, 'hour')

  if (hours < 24) {
    return `${hours} 小时`
  } else {
    const days = Math.floor(hours / 24)
    const remainingHours = hours % 24
    return remainingHours > 0 ? `${days} 天 ${remainingHours} 小时` : `${days} 天`
  }
}

// 用于Ant Design Vue DatePicker的值转换
// 注意：为了确保与 Ant Design Vue 4.x 完全兼容，这些函数现在返回/接收 dayjs 对象
import dayjs, { type Dayjs } from 'dayjs'

export const toDatePickerValue = (isoString: string): Dayjs | null => {
  if (!isoString) return null
  const dayjsObj = dayjs(isoString)
  return dayjsObj.isValid() ? dayjsObj : null
}

export const fromDatePickerValue = (date: Dayjs | null): string => {
  if (!date) return ''
  return date.toISOString()
}

// 创建 DateInstance 的便捷函数
export const createDateInstance = (input?: Date | string | number): DateInstance => {
  return dateUtils(input)
}

// 添加天数
export const addDays = (date: Date | string | number, days: number): DateInstance => {
  return dateUtils(date).add(days, 'day')
}

// 判断是否是同一天
export const isSameDay = (
  date1: Date | string | number,
  date2: Date | string | number
): boolean => {
  const d1 = dateUtils(date1)
  const d2 = dateUtils(date2)
  return d1.format('YYYY-MM-DD') === d2.format('YYYY-MM-DD')
}

console.log('混合Date工具函数已加载，DatePicker兼容函数已更新为dayjs')

export default dateUtils
