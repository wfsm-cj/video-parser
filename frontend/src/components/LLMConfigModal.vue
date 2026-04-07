<template>
  <Teleport to="body">
    <div v-if="visible" class="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="$emit('close')"></div>
      <div class="relative w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden">
        <div class="flex items-center justify-between px-6 py-4 border-b">
          <h3 class="text-lg font-semibold">AI 模型配置</h3>
          <button @click="$emit('close')" class="p-1 rounded-lg hover:bg-gray-100">
            <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">选择厂商</label>
            <select v-model="provider" @change="onProviderChange" class="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-blue-500 outline-none">
              <option v-for="(info, key) in providers" :key="key" :value="key">{{ info.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">选择模型</label>
            <select v-model="model" class="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-blue-500 outline-none">
              <option v-for="m in models" :key="m" :value="m">{{ m }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">API Key</label>
            <input v-model="apiKey" type="password" placeholder="请输入 API Key" class="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-blue-500 outline-none" />
          </div>
        </div>
        <div class="px-6 py-4 bg-gray-50 flex gap-3">
          <button @click="$emit('close')" class="flex-1 py-2.5 rounded-xl border border-gray-200 font-medium hover:bg-gray-100">取消</button>
          <button @click="save" :disabled="!apiKey" :class="['flex-1', 'py-2.5', 'rounded-xl', 'font-medium', apiKey ? 'bg-blue-500 text-white hover:bg-blue-600' : 'bg-gray-200 text-gray-400 cursor-not-allowed']">保存</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['close', 'save'])

const providers = ref({})
const provider = ref('deepseek')
const model = ref('')
const apiKey = ref('')

const models = computed(() => providers.value[provider.value]?.models || [])

async function load() {
  try {
    const [pRes, cRes] = await Promise.all([fetch('/api/llm/providers'), fetch('/api/llm/config')])
    providers.value = await pRes.json()
    const config = await cRes.json()
    if (config.provider && providers.value[config.provider]) {
      provider.value = config.provider
    }
    model.value = config.model || models.value[0] || ''
  } catch (e) {
    console.error(e)
  }
}

function onProviderChange() {
  model.value = models.value[0] || ''
}

async function save() {
  if (!apiKey.value) return
  try {
    const res = await fetch('/api/llm/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: provider.value, api_key: apiKey.value, model: model.value })
    })
    if (!res.ok) throw new Error('保存失败')
    emit('save', { provider: provider.value, model: model.value })
    emit('close')
  } catch (e) {
    alert(e.message)
  }
}

watch(() => props.visible, v => { if (v) load() })
</script>
