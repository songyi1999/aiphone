<template>
  <div class="knowledge-base">
    <h1>个人知识库</h1>
    <div class="controls">
      <button @click="fetchKnowledgeItems">刷新</button>
      <button @click="showAddForm = !showAddForm">
        {{ showAddForm ? '取消添加' : '添加知识条目' }}
      </button>
      <button @click="showVoiceInput = !showVoiceInput">
        {{ showVoiceInput ? '关闭语音输入' : '语音输入' }}
      </button>
      <button @click="getLocation">获取当前位置</button>
    </div>
    
    <!-- 语音输入组件 -->
    <div v-if="showVoiceInput" class="voice-input">
      <h2>语音输入</h2>
      <div class="recording-controls">
        <button @click="startRecording" :disabled="isRecording">
          {{ isRecording ? '录音中...' : '开始录音' }}
        </button>
        <button @click="stopRecording" :disabled="!isRecording">
          停止录音
        </button>
      </div>
      <div v-if="transcribedText" class="transcribed-text">
        <h3>识别结果：</h3>
        <p>{{ transcribedText }}</p>
        <button @click="useTranscribedText">使用识别文本</button>
      </div>
    </div>
    
    <!-- 添加知识条目表单 -->
    <div v-if="showAddForm" class="add-form">
      <h2>添加新知识条目</h2>
      <form @submit.prevent="addKnowledgeItem">
        <div>
          <label for="title">标题:</label>
          <input id="title" v-model="newItem.title" required />
        </div>
        <div>
          <label for="content">内容:</label>
          <textarea id="content" v-model="newItem.content" required></textarea>
        </div>
        <div>
          <label for="category">分类:</label>
          <input id="category" v-model="newItem.category" required />
        </div>
        <div>
          <label for="location">位置:</label>
          <input id="location" v-model="newItem.location" />
        </div>
        <div v-if="currentLocation" class="location-info">
          <p>当前坐标: {{ currentLocation.latitude }}, {{ currentLocation.longitude }}</p>
        </div>
        <button type="submit">添加</button>
      </form>
    </div>
    
    <!-- 知识条目列表 -->
    <div v-if="knowledgeItems.length > 0" class="knowledge-list">
      <h2>知识条目列表</h2>
      <div v-for="item in knowledgeItems" :key="item.id" class="knowledge-item">
        <h3>{{ item.title }}</h3>
        <p>{{ item.content }}</p>
        <p><strong>分类:</strong> {{ item.category }}</p>
        <p v-if="item.location"><strong>位置:</strong> {{ item.location }}</p>
        <div class="item-actions">
          <button @click="editItem(item)">编辑</button>
          <button @click="deleteItem(item.id)">删除</button>
        </div>
      </div>
    </div>
    
    <div v-else>
      <p>暂无知识条目</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { KnowledgeItem } from '@/types'

// 知识条目列表
const knowledgeItems = ref<KnowledgeItem[]>([])

// 控制添加表单显示
const showAddForm = ref(false)

// 控制语音输入显示
const showVoiceInput = ref(false)

// 新条目数据
const newItem = ref<KnowledgeItem>({
  id: 0,
  title: '',
  content: '',
  category: '',
  location: '',
  latitude: undefined,
  longitude: undefined
})

// 当前位置信息
const currentLocation = ref<{ latitude: number; longitude: number } | null>(null)

// 语音识别相关
const isRecording = ref(false)
const mediaRecorder = ref<MediaRecorder | null>(null)
const audioChunks = ref<Blob[]>([])
const transcribedText = ref('')

// 编辑中的条目
const editingItem = ref<KnowledgeItem | null>(null)

// 获取知识条目列表
const fetchKnowledgeItems = async () => {
  try {
    const response = await fetch('http://localhost:8000/knowledge')
    knowledgeItems.value = await response.json()
  } catch (error) {
    console.error('获取知识条目失败:', error)
  }
}

// 添加知识条目
const addKnowledgeItem = async () => {
  try {
    // 如果有当前位置信息，添加到 newItem
    if (currentLocation.value) {
      newItem.value.latitude = currentLocation.value.latitude
      newItem.value.longitude = currentLocation.value.longitude
    }
    
    const response = await fetch('http://localhost:8000/knowledge', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(newItem.value)
    })
    
    const addedItem = await response.json()
    knowledgeItems.value.push(addedItem)
    
    // 重置表单
    newItem.value = {
      id: 0,
      title: '',
      content: '',
      category: '',
      location: '',
      latitude: undefined,
      longitude: undefined
    }
    
    showAddForm.value = false
    currentLocation.value = null
  } catch (error) {
    console.error('添加知识条目失败:', error)
  }
}

// 编辑条目
const editItem = (item: KnowledgeItem) => {
  editingItem.value = { ...item }
  newItem.value = { ...item }
  showAddForm.value = true
}

// 删除条目
const deleteItem = async (id: number) => {
  if (!confirm('确定要删除这个条目吗？')) return
  
  try {
    await fetch(`http://localhost:8000/knowledge/${id}`, {
      method: 'DELETE'
    })
    
    // 从列表中移除
    knowledgeItems.value = knowledgeItems.value.filter(item => item.id !== id)
  } catch (error) {
    console.error('删除知识条目失败:', error)
  }
}

// 开始录音
const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder.value = new MediaRecorder(stream)
    audioChunks.value = []
    
    mediaRecorder.value.ondataavailable = (event) => {
      audioChunks.value.push(event.data)
    }
    
    mediaRecorder.value.start()
    isRecording.value = true
  } catch (error) {
    console.error('无法访问麦克风:', error)
    alert('无法访问麦克风，请检查权限设置')
  }
}

// 停止录音并上传
const stopRecording = async () => {
  if (!mediaRecorder.value) return
  
  mediaRecorder.value.stop()
  isRecording.value = false
  
  mediaRecorder.value.onstop = async () => {
    try {
      // 创建音频文件
      const audioBlob = new Blob(audioChunks.value, { type: 'audio/wav' })
      const formData = new FormData()
      formData.append('file', audioBlob, 'recording.wav')
      
      // 上传到后端进行语音识别
      const response = await fetch('http://localhost:8000/transcribe', {
        method: 'POST',
        body: formData
      })
      
      const result = await response.json()
      transcribedText.value = result.text
    } catch (error) {
      console.error('语音识别失败:', error)
      alert('语音识别失败，请重试')
    }
  }
}

// 使用识别的文本
const useTranscribedText = () => {
  newItem.value.content = transcribedText.value
  transcribedText.value = ''
  showVoiceInput.value = false
  showAddForm.value = true
}

// 获取当前位置
const getLocation = () => {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        currentLocation.value = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        }
        showAddForm.value = true
      },
      (error) => {
        console.error('获取位置失败:', error)
        alert('获取位置失败，请检查权限设置')
      }
    )
  } else {
    alert('浏览器不支持地理定位')
  }
}

// 初始化获取数据
onMounted(() => {
  fetchKnowledgeItems()
})
</script>

<style scoped>
.knowledge-base {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.controls {
  margin-bottom: 20px;
}

.controls button {
  margin-right: 10px;
  padding: 8px 16px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.controls button:hover {
  background-color: #359c6d;
}

.controls button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.voice-input {
  background-color: #f5f5f5;
  padding: 20px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.recording-controls {
  margin-bottom: 15px;
}

.recording-controls button {
  margin-right: 10px;
  padding: 8px 16px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.recording-controls button:hover {
  background-color: #359c6d;
}

.recording-controls button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.transcribed-text {
  background-color: #e8f5e9;
  padding: 15px;
  border-radius: 4px;
  margin-top: 15px;
}

.transcribed-text h3 {
  margin-top: 0;
}

.transcribed-text button {
  margin-top: 10px;
  padding: 5px 10px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.location-info {
  background-color: #e3f2fd;
  padding: 10px;
  border-radius: 4px;
  margin: 10px 0;
}

.add-form {
  background-color: #f5f5f5;
  padding: 20px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.add-form form div {
  margin-bottom: 15px;
}

.add-form label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.add-form input,
.add-form textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box;
}

.add-form textarea {
  height: 100px;
  resize: vertical;
}

.add-form button {
  padding: 10px 20px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.add-form button:hover {
  background-color: #359c6d;
}

.knowledge-list {
  margin-top: 20px;
}

.knowledge-item {
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 15px;
  margin-bottom: 15px;
  background-color: #fff;
}

.knowledge-item h3 {
  margin-top: 0;
  color: #333;
}

.item-actions {
  margin-top: 10px;
}

.item-actions button {
  margin-right: 10px;
  padding: 5px 10px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.item-actions button:hover {
  background-color: #359c6d;
}
</style>