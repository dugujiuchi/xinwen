<template>
  <div class="tag-filter">
    <button
      v-for="tag in tags"
      :key="tag.key"
      :class="['tag-item', { active: modelValue === tag.key }]"
      @click="$emit('update:modelValue', tag.key)"
    >
      {{ tag.label }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  tags: { type: Array, required: true },
  modelValue: { type: String, default: '' },
})
defineEmits(['update:modelValue'])
</script>
