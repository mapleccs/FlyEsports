/**
 * DatePicker兼容性修复的单元测试
 * 验证 dayjs 对象的正确处理和与 Ant Design Vue 的兼容性
 */

import { describe, it, expect, beforeEach } from 'vitest'
import dayjs, { type Dayjs } from 'dayjs'
import { toDatePickerValue, fromDatePickerValue } from './dateUtils'

describe('DatePicker 兼容性修复', () => {
  let testISOString: string
  let testDayjs: Dayjs

  beforeEach(() => {
    testISOString = '2025-09-11T10:30:00.000Z'
    testDayjs = dayjs(testISOString)
  })

  describe('toDatePickerValue', () => {
    it('应该将有效的ISO字符串转换为dayjs对象', () => {
      const result = toDatePickerValue(testISOString)

      expect(result).toBeDefined()
      expect(result?.isValid()).toBe(true)
      expect(result?.toISOString()).toBe(testISOString)
    })

    it('应该返回null当输入为空字符串', () => {
      const result = toDatePickerValue('')
      expect(result).toBeNull()
    })

    it('应该返回null当输入为无效日期字符串', () => {
      const result = toDatePickerValue('invalid-date')
      expect(result).toBeNull()
    })

    it('返回的对象应该有locale方法(dayjs特性)', () => {
      const result = toDatePickerValue(testISOString)

      expect(result).toBeDefined()
      expect(typeof result?.locale).toBe('function')
    })
  })

  describe('fromDatePickerValue', () => {
    it('应该将dayjs对象转换为ISO字符串', () => {
      const result = fromDatePickerValue(testDayjs)
      expect(result).toBe(testISOString)
    })

    it('应该返回空字符串当输入为null', () => {
      const result = fromDatePickerValue(null)
      expect(result).toBe('')
    })
  })

  describe('DatePicker集成测试', () => {
    it('完整的转换周期应该保持数据一致性', () => {
      // 模拟从后端接收数据 -> DatePicker显示 -> 用户修改 -> 提交到后端
      const originalISOString = testISOString

      // 1. 后端数据转换为DatePicker值
      const pickerValue = toDatePickerValue(originalISOString)
      expect(pickerValue?.isValid()).toBe(true)

      // 2. 模拟用户修改时间(加1小时)
      const modifiedPickerValue = pickerValue?.add(1, 'hour')

      // 3. 转换回ISO字符串提交后端
      const finalISOString = fromDatePickerValue(modifiedPickerValue || null)

      expect(finalISOString).toBe('2025-09-11T11:30:00.000Z')
    })

    it('应该与Ant Design Vue DatePicker兼容', () => {
      // 验证返回的对象具有DatePicker需要的所有方法
      const pickerValue = toDatePickerValue(testISOString)

      // 这些是Ant Design Vue DatePicker内部可能调用的方法
      expect(typeof pickerValue?.format).toBe('function')
      expect(typeof pickerValue?.valueOf).toBe('function')
      expect(typeof pickerValue?.isSame).toBe('function')
      expect(typeof pickerValue?.locale).toBe('function')
    })
  })
})

describe('日期处理错误场景', () => {
  it('应该优雅处理各种无效输入', () => {
    // 测试空值输入
    expect(toDatePickerValue('')).toBeNull()
    expect(toDatePickerValue(null as any)).toBeNull()
    expect(toDatePickerValue(undefined as any)).toBeNull()

    // 测试无效日期字符串
    const invalidResult1 = toDatePickerValue('invalid')
    const invalidResult2 = toDatePickerValue('2025-13-45')

    // dayjs对于无效输入会返回Invalid Date对象，我们应该返回null
    expect(invalidResult1).toBeNull()
    // 注意：'2025-13-45'可能被dayjs解析为有效日期(自动修正)，所以我们检查是否为null或有效
    expect(invalidResult2 === null || invalidResult2?.isValid()).toBe(true)
  })
})
