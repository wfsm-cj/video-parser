<template>
  <Teleport to="body">
    <div v-if="visible" class="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="$emit('close')"></div>
      <div class="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden">
        <div class="flex items-center justify-between px-6 py-4 border-b">
          <h3 class="text-lg font-semibold">B站 Cookie 配置</h3>
          <button @click="$emit('close')" class="p-1 rounded-lg hover:bg-gray-100">
            <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="p-6 space-y-4">
          <div class="bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-sm text-yellow-800">
            <p class="font-medium mb-1">💡 如何获取 Cookie？</p>
            <ol class="list-decimal list-inside space-y-1 text-yellow-700">
              <li>登录 B站网页版 (bilibili.com)</li>
              <li>按 F12 打开开发者工具</li>
              <li>切换到 Application/应用 → Cookies → bilibili.com</li>
              <li>复制 Cookie 字符串，粘贴到下方</li>
            </ol>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Cookie 字符串</label>
            <textarea v-model="cookie" rows="4" placeholder="SESSDATA=xxx; bili_jct=xxx; ..." class="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-blue-500 outline-none text-sm font-mono"></textarea>
          </div>
          <div class="flex items-center gap-3">
            <input type="checkbox" id="enabled" v-model="enabled" class="w-4 h-4 text-blue-500 rounded" />
            <label for="enabled" class="text-sm text-gray-700">启用 Cookie（解析 B站视频时使用）</label>
          </div>
          <div v-if="success" class="px-4 py-3 rounded-xl text-sm bg-green-50 text-green-700">{{ success }}</div>
        </div>
        <div class="px-6 py-4 bg-gray-50 flex gap-3">
          <button @click="$emit('close')" class="flex-1 py-2.5 rounded-xl border border-gray-200 font-medium hover:bg-gray-100">取消</button>
          <button @click="save" :disabled="loading" class="flex-1 py-2.5 rounded-xl bg-blue-500 text-white font-medium hover:bg-blue-600 disabled:opacity-50">
            {{ loading ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['close'])

const cookie = ref('')
const enabled = ref(false)
const loading = ref(false)
const success = ref('')

async function load() {
  try {
    const res = await fetch('/api/bili-cookie/config')
    const data = await res.json()
    enabled.value = data.enabled
  } catch (e) {
    console.error(e)
  }
}

async function save() {
  loading.value = true
  success.value = ''
  try {
    const res = await fetch('/api/bili-cookie/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookie: cookie.value, enabled: enabled.value })
    })
    if (!res.ok) throw new Error('保存失败')
    success.value = '保存成功！'
    setTimeout(() => emit('close'), 1000)
  } catch (e) {
    alert(e.message)
  } finally {
    loading.value = false
  }
}

watch(() => props.visible, v => { if (v) { load(); success.value = '' } })
</script>
