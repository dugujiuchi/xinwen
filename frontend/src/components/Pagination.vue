<template>
  <div v-if="totalPages > 1" class="pagination">
    <button
      v-for="p in visiblePages"
      :key="p"
      :class="['page-btn', { active: p === modelValue }]"
      @click="$emit('update:modelValue', p)"
    >
      {{ p }}
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Number, default: 1 },
  total: { type: Number, default: 0 },
  size: { type: Number, default: 20 },
})
defineEmits(['update:modelValue'])

const totalPages = computed(() => Math.ceil(props.total / props.size) || 1)
const visiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, props.modelValue - 2)
  const end = Math.min(totalPages.value, props.modelValue + 2)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})
</script>
