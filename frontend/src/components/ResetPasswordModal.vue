<template>
  <Teleport to="body">
    <div v-if="visible" class="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="$emit('close')"></div>
      <div class="relative w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden">
        <div class="flex items-center justify-between px-6 py-4 border-b">
          <h3 class="text-lg font-semibold">重置密码</h3>
          <button @click="$emit('close')" class="p-1 rounded-lg hover:bg-gray-100">
            <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">原密码</label>
            <input v-model="oldPassword" type="password" placeholder="请输入原密码" class="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">新密码</label>
            <input v-model="newPassword" type="password" placeholder="请输入新密码" class="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">确认新密码</label>
            <input v-model="confirmPassword" type="password" placeholder="请再次输入新密码" class="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-blue-500 outline-none" />
          </div>
          <div v-if="error" class="px-4 py-3 rounded-xl text-sm bg-red-50 text-red-700">{{ error }}</div>
        </div>
        <div class="px-6 py-4 bg-gray-50 flex gap-3">
          <button @click="$emit('close')" class="flex-1 py-2.5 rounded-xl border border-gray-200 font-medium hover:bg-gray-100">取消</button>
          <button @click="handleSubmit" :disabled="loading" class="flex-1 py-2.5 rounded-xl bg-blue-500 text-white font-medium hover:bg-blue-600 disabled:opacity-50">
            {{ loading ? '提交中...' : '确认修改' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import { resetPassword } from '../api/auth.js'

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['close', 'success'])

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')

async function handleSubmit() {
  error.value = ''
  if (!oldPassword.value || !newPassword.value || !confirmPassword.value) {
    error.value = '请填写所有字段'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  if (newPassword.value.length < 6) {
    error.value = '密码长度至少6位'
    return
  }

  loading.value = true
  try {
    await resetPassword(oldPassword.value, newPassword.value)
    emit('success', '密码修改成功')
    emit('close')
  } catch (e) {
    error.value = e.response?.data?.detail || '修改失败'
  } finally {
    loading.value = false
  }
}
</script>
