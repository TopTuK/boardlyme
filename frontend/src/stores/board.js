import { defineStore } from 'pinia'
import api, { tryRefresh } from '../api/client'

const POLL_INTERVAL_MS = 4000

function sortTasks(a, b) {
  if (a.position !== b.position) return a.position - b.position
  return a.created_at < b.created_at ? -1 : 1
}

export const useBoardStore = defineStore('board', {
  state: () => ({
    project: null,
    stages: [],
    tasks: [],
    members: [],
    // stage_id -> { active: Task[], done: Task[] }. Arrays are mutated in
    // place so vuedraggable bindings stay valid across rebuilds.
    tasksByStage: {},
    loading: false,
    error: '',
    wsStatus: 'off', // 'off' | 'connecting' | 'on'
    polling: false, // HTTP fallback while the WebSocket is unavailable
    _ws: null,
    _projectId: null,
    _reconnectTimer: null,
    _pingTimer: null,
    _pollTimer: null,
  }),

  getters: {
    visibleStages: (s) => s.stages.filter((st) => !st.is_hidden),
    doneStage: (s) => s.stages.find((st) => st.is_done) || null,
    firstWorkStage: (s) =>
      s.stages.filter((st) => !st.is_done).sort((a, b) => a.position - b.position)[0] || null,
  },

  actions: {
    _fail(e, fallback) {
      this.error = e?.response?.data?.detail || fallback
    },

    setBoard({ project, stages, tasks, members }) {
      this.project = project
      this.stages = stages
      this.tasks = tasks
      this.members = members
      this.rebuild()
    },

    /** Recompute tasksByStage lanes from the flat task list, preserving array identities. */
    rebuild() {
      const grouped = {}
      for (const s of this.stages) grouped[s.id] = { active: [], done: [] }
      for (const t of [...this.tasks].sort(sortTasks)) {
        if (!grouped[t.stage_id]) grouped[t.stage_id] = { active: [], done: [] }
        grouped[t.stage_id][t.stage_done ? 'done' : 'active'].push(t)
      }
      for (const [stageId, lanes] of Object.entries(grouped)) {
        let slot = this.tasksByStage[stageId]
        if (!slot || !slot.active || !slot.done) {
          slot = this.tasksByStage[stageId] = { active: [], done: [] }
        }
        slot.active.splice(0, slot.active.length, ...lanes.active)
        slot.done.splice(0, slot.done.length, ...lanes.done)
      }
      for (const stageId of Object.keys(this.tasksByStage)) {
        if (!(stageId in grouped)) delete this.tasksByStage[stageId]
      }
    },

    lanes(stageId) {
      if (!this.tasksByStage[stageId]) this.tasksByStage[stageId] = { active: [], done: [] }
      return this.tasksByStage[stageId]
    },

    upsertTask(task) {
      const idx = this.tasks.findIndex((t) => t.id === task.id)
      if (idx >= 0) this.tasks.splice(idx, 1, task)
      else this.tasks.push(task)
      this.rebuild()
    },

    applyEvent(ev) {
      if (!ev || !ev.type) return
      switch (ev.type) {
        case 'task.created':
        case 'task.updated':
          if (ev.task) this.upsertTask(ev.task)
          break

        case 'tasks.reordered':
          for (const brief of ev.tasks || []) {
            const task = this.tasks.find((t) => t.id === brief.id)
            if (task) {
              task.stage_id = brief.stage_id
              task.position = brief.position
              task.stage_done = !!brief.stage_done
              task.completed_at = brief.completed_at || null
            }
          }
          this.rebuild()
          break

        case 'task.deleted':
          this.tasks = this.tasks.filter((t) => t.id !== ev.task_id)
          this.rebuild()
          break

        case 'stage.created':
          if (Array.isArray(ev.stages)) {
            this.stages = ev.stages
          } else if (ev.stage && !this.stages.some((s) => s.id === ev.stage.id)) {
            // Fallback for the local add-stage path (no full list): insert
            // right before Done — the server pins Done last, and its stale
            // local position must not tie-break the new stage behind it.
            const doneIdx = this.stages.findIndex((s) => s.is_done)
            this.stages.splice(doneIdx === -1 ? this.stages.length : doneIdx, 0, ev.stage)
          }
          this.rebuild()
          break

        case 'stage.updated': {
          const idx = this.stages.findIndex((s) => s.id === ev.stage?.id)
          if (idx >= 0) this.stages.splice(idx, 1, ev.stage)
          break
        }

        case 'stage.reordered':
          if (Array.isArray(ev.stages)) this.stages = ev.stages
          break

        case 'stage.deleted':
          this.stages = this.stages.filter((s) => s.id !== ev.stage_id)
          this.tasks = this.tasks.filter((t) => t.stage_id !== ev.stage_id)
          this.rebuild()
          break

        case 'members.changed':
          this.members = ev.members || []
          break

        case 'project.updated':
          if (this.project && ev.project && this.project.id === ev.project.id) {
            this.project = { ...this.project, ...ev.project }
          }
          break

        default:
          break
      }
    },

    async fetchBoard(projectId) {
      this.loading = true
      this.error = ''
      try {
        const { data } = await api.get(`/projects/${projectId}`)
        this.setBoard(data)
      } catch (e) {
        this._fail(e, 'errors.loadBoard')
        throw e
      } finally {
        this.loading = false
      }
    },

    async createTask(stageId, payload) {
      const title = (typeof payload === 'string' ? payload : payload?.title || '').trim()
      const description = (typeof payload === 'string' ? '' : payload?.description || '').trim()
      const deadline = typeof payload === 'string' ? null : payload?.deadline || null
      const assigneeId = typeof payload === 'string' ? null : payload?.assignee_id || null
      if (!title || !this.project) return false
      try {
        const { data } = await api.post(`/projects/${this.project.id}/tasks`, {
          title,
          description: description || null,
          deadline,
          assignee_id: assigneeId,
          stage_id: stageId,
        })
        this.applyEvent({ type: 'task.created', task: data })
        return true
      } catch (e) {
        this._fail(e, 'errors.createTask')
        return false
      }
    },

    async updateTask(taskId, patch) {
      try {
        const { data } = await api.patch(`/tasks/${taskId}`, patch)
        this.applyEvent({ type: 'task.updated', task: data })
        return true
      } catch (e) {
        this._fail(e, 'errors.saveTask')
        return false
      }
    },

    /** lane=false -> active sub-stage, lane=true -> done sub-stage (split stages). */
    async moveTask(taskId, stageId, index, lane = false) {
      if (!this.project) return
      try {
        const { data } = await api.post(`/tasks/${taskId}/move`, {
          stage_id: stageId,
          index,
          stage_done: lane,
        })
        this.applyEvent({ type: 'tasks.reordered', tasks: data.tasks })
      } catch (e) {
        this._fail(e, 'errors.moveTask')
        await this.fetchBoard(this.project.id).catch(() => {})
      }
    },

    async completeTask(taskId) {
      try {
        const { data } = await api.post(`/tasks/${taskId}/complete`)
        this.applyEvent({ type: 'tasks.reordered', tasks: data.tasks })
        return true
      } catch (e) {
        this._fail(e, 'errors.completeTask')
        return false
      }
    },

    async reopenTask(taskId) {
      const stage = this.firstWorkStage
      if (!stage) {
        this.error = 'errors.noWorkStage'
        return false
      }
      this.error = ''
      await this.moveTask(taskId, stage.id, 0)
      return !this.error
    },

    /** Move the task into the done sub-stage of its (split) stage. */
    async sendToStageDone(taskId) {
      const task = this.tasks.find((t) => t.id === taskId)
      if (!task) return false
      await this.moveTask(taskId, task.stage_id, 10 ** 9, true)
      return !this.error
    },

    /** Move the task back into the active sub-stage of its (split) stage. */
    async returnToStageActive(taskId) {
      const task = this.tasks.find((t) => t.id === taskId)
      if (!task) return false
      await this.moveTask(taskId, task.stage_id, 0, false)
      return !this.error
    },

    async deleteTask(taskId) {
      try {
        await api.delete(`/tasks/${taskId}`)
        this.applyEvent({ type: 'task.deleted', task_id: taskId })
        return true
      } catch (e) {
        this._fail(e, 'errors.deleteTask')
        return false
      }
    },

    // ------------------------------------------------------------------ #
    // Checklist
    // ------------------------------------------------------------------ #

    async addChecklistItem(taskId, content) {
      try {
        const { data } = await api.post(`/tasks/${taskId}/checklist`, { content })
        this.applyEvent({ type: 'task.updated', task: data })
        return true
      } catch (e) {
        this._fail(e, 'errors.checklist')
        return false
      }
    },

    async updateChecklistItem(taskId, itemId, patch) {
      try {
        const { data } = await api.patch(`/checklist/items/${itemId}`, patch)
        this.applyEvent({ type: 'task.updated', task: data })
        return true
      } catch (e) {
        this._fail(e, 'errors.checklist')
        return false
      }
    },

    async removeChecklistItem(taskId, itemId) {
      // The endpoint returns no body — drop the item locally (the WS
      // broadcast upserts the full task for the other clients anyway).
      const task = this.tasks.find((t) => t.id === taskId)
      const backup = task?.checklist
      if (task) task.checklist = (task.checklist || []).filter((i) => i.id !== itemId)
      try {
        await api.delete(`/checklist/items/${itemId}`)
        return true
      } catch (e) {
        if (task) task.checklist = backup
        this._fail(e, 'errors.checklist')
        return false
      }
    },

    async addStage(name, wipLimit = null) {
      if (!this.project || !name.trim()) return false
      try {
        const { data } = await api.post(`/projects/${this.project.id}/stages`, {
          name,
          wip_limit: wipLimit,
        })
        this.applyEvent({ type: 'stage.created', stage: data })
        return true
      } catch (e) {
        this._fail(e, 'errors.addStage')
        return false
      }
    },

    async updateStage(stageId, patch) {
      try {
        const { data } = await api.patch(`/stages/${stageId}`, patch)
        this.applyEvent({ type: 'stage.updated', stage: data })
        return true
      } catch (e) {
        this._fail(e, 'errors.updateStage')
        return false
      }
    },

    /**
     * Reorder columns. stageIds must be a permutation of every stage of the
     * project (hidden included) — the API pins Backlog first and Done last.
     */
    async reorderStages(stageIds) {
      if (!this.project) return false
      const byId = new Map(this.stages.map((s) => [s.id, s]))
      const next = stageIds.map((id) => byId.get(id)).filter(Boolean)
      if (next.length !== this.stages.length) return false
      const previous = this.stages
      this.stages = next.map((s, i) => ({ ...s, position: i }))
      try {
        const { data } = await api.put(`/projects/${this.project.id}/stages/reorder`, { stage_ids: stageIds })
        this.stages = data
        return true
      } catch (e) {
        this.stages = previous
        this._fail(e, 'errors.reorderStages')
        return false
      }
    },

    /** value: number to set the limit, null to clear it. */
    async setWipLimit(stageId, value) {
      return this.updateStage(stageId, { wip_limit: value })
    },

    async toggleSplit(stageId, value) {
      return this.updateStage(stageId, { is_split: value })
    },

    async deleteStage(stageId) {
      try {
        await api.delete(`/stages/${stageId}`)
        this.applyEvent({ type: 'stage.deleted', stage_id: stageId })
        return true
      } catch (e) {
        this._fail(e, 'errors.deleteStage')
        return false
      }
    },

    async renameProject(name) {
      if (!this.project || !name.trim()) return false
      try {
        const { data } = await api.patch(`/projects/${this.project.id}`, { name })
        this.applyEvent({ type: 'project.updated', project: data })
        return true
      } catch (e) {
        this._fail(e, 'errors.renameProject')
        return false
      }
    },

    async leaveProject() {
      if (!this.project) return false
      try {
        await api.post(`/projects/${this.project.id}/leave`)
        this.disconnectWS()
        return true
      } catch (e) {
        this._fail(e, 'errors.leaveProject')
        return false
      }
    },

    async deleteProject() {
      if (!this.project) return false
      try {
        await api.delete(`/projects/${this.project.id}`)
        this.disconnectWS()
        return true
      } catch (e) {
        this._fail(e, 'errors.deleteProject')
        return false
      }
    },

    async addMember(userId) {
      try {
        const { data } = await api.post(`/projects/${this.project.id}/members`, { user_id: userId })
        this.applyEvent({ type: 'members.changed', members: data })
        return true
      } catch (e) {
        this._fail(e, 'errors.addMember')
        return false
      }
    },

    async removeMember(userId) {
      try {
        await api.delete(`/projects/${this.project.id}/members/${userId}`)
        this.applyEvent({ type: 'members.changed', members: this.members.filter((m) => m.user_id !== userId) })
        return true
      } catch (e) {
        this._fail(e, 'errors.removeMember')
        return false
      }
    },

    async searchUsers(q) {
      try {
        const { data } = await api.get(`/projects/${this.project.id}/members/search`, {
          params: { q },
        })
        return data
      } catch {
        return []
      }
    },

    // ------------------------------------------------------------------ #
    // Live sync: WebSocket first, HTTP polling as an automatic fallback
    // (covers Telegram Mini App local development through tunnels that
    // break WebSocket upgrades).
    // ------------------------------------------------------------------ #

    connectWS(projectId) {
      this.disconnectWS()
      this._projectId = projectId
      this.wsStatus = 'connecting'

      const token = localStorage.getItem('bm_token')
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const url = `${proto}://${window.location.host}/api/ws/projects/${projectId}?token=${encodeURIComponent(token || '')}`
      const ws = new WebSocket(url)
      this._ws = ws

      ws.onopen = () => {
        if (this._projectId !== projectId) return
        this.wsStatus = 'on'
        this._stopPolling()
        this._pingTimer = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send('ping')
        }, 25000)
      }

      ws.onmessage = (event) => {
        try {
          this.applyEvent(JSON.parse(event.data))
        } catch {
          /* ignore malformed frames */
        }
      }

      ws.onclose = (event) => {
        clearInterval(this._pingTimer)
        this._pingTimer = null
        if (this._projectId !== projectId) return
        this.wsStatus = 'off'
        if (event.code === 4403) {
          this._stopPolling() // no longer a member — stop syncing entirely
          return
        }
        this._startPolling()
        this._reconnectTimer = setTimeout(async () => {
          if (this._projectId !== projectId) return
          if (event.code === 4401) await tryRefresh()
          if (this._projectId === projectId) this.connectWS(projectId)
        }, 2000)
      }
    },

    disconnectWS() {
      if (this._reconnectTimer) {
        clearTimeout(this._reconnectTimer)
        this._reconnectTimer = null
      }
      if (this._pingTimer) {
        clearInterval(this._pingTimer)
        this._pingTimer = null
      }
      this._stopPolling()
      this._projectId = null
      this.wsStatus = 'off'
      if (this._ws) {
        const ws = this._ws
        this._ws = null
        try {
          ws.close()
        } catch {
          /* ignore */
        }
      }
    },

    _startPolling() {
      if (this._pollTimer) return
      this.polling = true
      this._pollTimer = setInterval(async () => {
        if (!this._projectId || document.visibilityState !== 'visible') return
        try {
          const { data } = await api.get(`/projects/${this._projectId}`)
          this.setBoard(data)
        } catch {
          /* keep polling; the next tick may recover */
        }
      }, POLL_INTERVAL_MS)
    },

    _stopPolling() {
      if (this._pollTimer) {
        clearInterval(this._pollTimer)
        this._pollTimer = null
      }
      this.polling = false
    },
  },
})
