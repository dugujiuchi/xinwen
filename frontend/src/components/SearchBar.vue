<template>
  <input
    type="text"
    class="search-bar"
    :value="modelValue"
    @input="onInput"
    placeholder="搜索资讯标题、来源或内容..."
  />
</template>

<script setup>
const props = defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])

let timer = null
function onInput(e) {
  clearTimeout(timer)
  const val = e.target.value
  timer = setTimeout(() => {
    emit('update:modelValue', val)
  }, 300)
}
</script>
