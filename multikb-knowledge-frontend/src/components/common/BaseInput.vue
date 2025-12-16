<template>
  <el-input
    v-model="modelValue"
    :type="type"
    :placeholder="placeholder"
    :disabled="disabled"
    :clearable="clearable"
    :show-password="showPassword"
    :prefix-icon="prefixIcon"
    :suffix-icon="suffixIcon"
    @input="$emit('update:modelValue', $event)"
    @change="$emit('change', $event)"
    @focus="$emit('focus', $event)"
    @blur="$emit('blur', $event)"
  />
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string
  type?: 'text' | 'textarea' | 'password'
  placeholder?: string
  disabled?: boolean
  clearable?: boolean
  showPassword?: boolean
  prefixIcon?: string
  suffixIcon?: string
}>()

defineEmits(['update:modelValue', 'change', 'focus', 'blur'])
</script>

<style lang="scss" scoped>
// Base Input styles
</style>
