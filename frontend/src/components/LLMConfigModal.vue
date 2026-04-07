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
            <div class="flex gap-2">
              <select v-model="provider" class="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 focus:border-blue-500 outline-none">
                <option v-for="(info, key) in providers" :key="key" :value="key">{{ info.name }}</option>
              </select>
              <button @click="refreshModels" :disabled="loadingModels" class="px-3 py-2 bg-gray-100 rounded-xl hover:bg-gray-200 disabled:opacity-50">
                <svg :class="['w-5 h-5', loadingModels ? 'animate-spin' : '']" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
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
          <button @click="testApi" :disabled="!apiKey || !provider || !model || testing" class="w-full py-2.5 rounded-xl font-medium transition-colors flex items-center justify-center gap-2" :class="[apiKey && provider && model ? 'bg-green-500 text-white hover:bg-green-600' : 'bg-gray-100 text-gray-400 cursor-not-allowed']">
            <svg v-if="testing" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            {{ testing ? '测试中...' : '测试 API Key' }}
          </button>
          <div v-if="testResult" :class="['px-4 py-3 rounded-xl text-sm flex items-center gap-2', testResult === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700']">
            <svg v-if="testResult === 'success'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {{ testMessage }}
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
const models = ref([])
const loadingModels = ref(false)
const testing = ref(false)
const testResult = ref(null)
const testMessage = ref('')

async function loadProviders() {
  try {
    const res = await fetch('/api/llm/providers')
    providers.value = await res.json()
    await refreshModels()
  } catch (e) {
    console.error(e)
  }
}

async function refreshModels() {
  loadingModels.value = true
  try {
    const res = await fetch(`/api/llm/providers/${provider.value}`)
    const data = await res.json()
    models.value = data.models || []
    if (models.value.length > 0 && !models.value.includes(model.value)) {
      model.value = models.value[0]
    }
  } catch (e) {
    console.error(e)
  } finally {
    loadingModels.value = false
  }
}

async function testApi() {
  if (!apiKey.value || !provider.value || !model.value) return
  testing.value = true
  testResult.value = null
  testMessage.value = ''
  try {
    const res = await fetch('/api/llm/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: provider.value, api_key: apiKey.value, model: model.value })
    })
    const data = await res.json()
    if (data.valid) {
      testResult.value = 'success'
      testMessage.value = 'API Key 测试成功！'
    } else {
      testResult.value = 'error'
      testMessage.value = data.message || '测试失败'
    }
  } catch (e) {
    testResult.value = 'error'
    testMessage.value = '请求失败，请检查网络'
  } finally {
    testing.value = false
  }
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

watch(() => props.visible, v => {
  if (v) {
    loadProviders()
    testResult.value = null
    testMessage.value = ''
  }
})

watch(provider, () => {
  refreshModels()
})
</script>
