<template>
  <div class="admin-page">
    <div class="admin-card">
      <h2>Quản lý Users & Conversations</h2>

      <table>
        <thead>
          <tr>
            <th>Username</th>
            <th>Role</th>
            <th>Ngày tạo User</th>
            <th>Tiêu đề đoạn chat</th>
            <th>Ngày tạo Chat</th>
            <th>Hành động</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="row in rows" :key="row.user_id + '-' + row.conversation_id">
            <td>{{ row.username }}</td>
            <td>{{ row.role }}</td>
            <td>{{ formatDate(row.user_created_at) }}</td>
            <td>{{ row.title_character || '—' }}</td>
            <td>{{ formatDate(row.conversation_created_at) }}</td>
            <td class="actions">
              <button class="btn btn-edit" @click="openEditModal(row)">
                Edit
              </button>
              <button class="btn btn-delete" @click="openDeleteModal(row)">
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <p v-if="rows.length === 0" class="empty">Không có dữ liệu</p>
    </div>

    <!-- ================= EDIT MODAL ================= -->
    <div v-if="showEdit" class="modal-overlay">
      <div class="admin-modal-card">
        <h2>Chỉnh sửa User</h2>

        <div class="form-group">
          <label>Username</label>
          <input
            v-model="editForm.username"
            placeholder="Nhập username..."
          />
        </div>

        <div class="form-group">
          <label>Password (để trống nếu không đổi)</label>
          <input
            type="password"
            v-model="editForm.password"
            placeholder="Nhập mật khẩu mới..."
          />
        </div>

        <div class="form-group">
          <label>Role</label>
          <select v-model="editForm.role">
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        </div>

        <div class="modal-actions">
          <button class="btn btn1" @click="submitEdit">Lưu</button>
          <button class="btn btn3" @click="closeEdit">Hủy</button>
        </div>
      </div>
    </div>

    <!-- ================= DELETE MODAL ================= -->
    <!-- DELETE CONFIRM MODAL -->
    <div v-if="showDelete" class="modal-overlay">
      <div class="admin-modal-card">
        <h2>Xác nhận xóa</h2>

        <p>
          Bạn có chắc muốn xóa user
          <b>{{ deleteTarget?.username }}</b>?
        </p>

        <p class="warn">
          ⚠️ Toàn bộ conversation sẽ bị xóa!
        </p>

        <div class="modal-actions">
          <button class="btn btn2" @click="confirmDelete">Xóa</button>
          <button class="btn btn3" @click="closeDelete">Hủy</button>
        </div>
      </div>
    </div>


  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'

const rows = ref([])

const showEdit = ref(false)
const showDelete = ref(false)

const editForm = ref({
  user_id: null,
  username: '',
  role: ''
})

const deleteTarget = ref(null)

onMounted(loadData)

async function loadData() {
  const res = await api.get('/admin/users')
  rows.value = res.data
}

/* ================= EDIT ================= */
function openEditModal(row) {
  editForm.value = {
    user_id: row.user_id,
    username: row.username,
    password:'',
    role: row.role
  }
  showEdit.value = true
}

function closeEdit() {
  showEdit.value = false
}

async function submitEdit() {
  await api.put(`/admin/users/${editForm.value.user_id}`, {
    username: editForm.value.username,
    password: editForm.value.password || null,
    role: editForm.value.role
  })

  // cập nhật lại local table
  rows.value.forEach(r => {
    if (r.user_id === editForm.value.user_id) {
      r.username = editForm.value.username
      r.role = editForm.value.role
    }
  })

  showEdit.value = false
}


/* ================= DELETE ================= */
function openDeleteModal(row) {
  deleteTarget.value = row
  showDelete.value = true
}

function closeDelete() {
  showDelete.value = false
}

async function confirmDelete() {
  await api.delete(`/admin/users/${deleteTarget.value.user_id}`)
  rows.value = rows.value.filter(r => r.user_id !== deleteTarget.value.user_id)
  showDelete.value = false
}

/* ================= UTILS ================= */
function formatDate(date) {
  if (!date) return '—'
  return new Date(date).toLocaleString()
}
</script>

<style scoped>
/* ================= PAGE LAYOUT ================= */
.admin-page {
  width: 100vw;
  min-height: calc(100vh - 64px);
  padding-top: 64px;

  background: linear-gradient(120deg, #667eea, #764ba2);
  display: flex;
  justify-content: center;
  padding: 40px;
}

 .admin-card {
  background: rgba(255, 255, 255, 0.95);
  padding: 30px;
  border-radius: 15px;
  width: 100%;
  max-width: 1100px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25);
}
.admin-modal-card{
   background: rgba(255, 255, 255, 0.95);
  padding: 40px 50px;
  border-radius: 15px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25);
  width: 100%;
  max-width: 400px;
  text-align: center;
  animation: fadeIn 0.6s ease-in-out;
} 
/* ================= TABLE ================= */
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

th, td {
  padding: 10px;
  border-bottom: 1px solid #ddd;
}

th {
  background: #667eea;
  color: white;
}

.actions {
  display: flex;
  gap: 8px;
}

/* ================= BUTTON ================= */
.btn {
  padding: 8px 12px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  font-weight: 600;
  transition: 0.25s;
}

.btn-edit {
  background: #f39c12;
  color: white;
}
.btn-edit:hover {
  background: #d68910;
}

.btn-delete {
  background: #e74c3c;
  color: white;
}
.btn-delete:hover {
  background: #c0392b;
}

.btn-save {
  background: #667eea;
  color: white;
}
.btn-save:hover {
  background: #5563de;
}

.btn-cancel {
  background: #aaa;
  color: white;
}
.btn-cancel:hover {
  background: #888;
}

/* ================= MODAL OVERLAY ================= */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

/* ================= MODAL CARD (GIỐNG LOGIN) ================= */
.modal-card {
  background: rgba(255, 255, 255, 0.95);
  padding: 35px 40px;
  border-radius: 15px;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25);
  animation: fadeIn 0.4s ease-in-out;
}

.modal-card h3 {
  text-align: center;
  margin-bottom: 20px;
  color: #333;
  font-weight: 600;
}

/* ================= FORM ================= */
.form-group {
  margin-bottom: 18px;
  text-align: left;
}

label {
  display: block;
  font-size: 14px;
  margin-bottom: 6px;
  color: #555;
}

input{
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #ccc;
  font-size: 15px;
  outline: none;
  transition: 0.2s;
}
.btn1{
  background-color: #0d6efd;
  color: white;
}

.btn3{
  background-color: #6c757d;
  color: white;
}
.btn2{
  background-color: #dc3545;
  color: white;
}
select {
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #ccc;
  font-size: 15px;
  outline: none;
  transition: 0.2s;
}

.modal-card input:focus,
.modal-card select:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
}

/* ================= MODAL ACTIONS ================= */
.modal-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 25px;
}

/* ================= WARNING ================= */
.warn {
  color: #e74c3c;
  font-weight: 600;
  margin-top: 10px;
}

/* ================= ANIMATION ================= */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(15px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

</style>
