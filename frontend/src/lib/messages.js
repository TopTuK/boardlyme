import { i18n } from '../i18n'

const CANONICAL_STAGES = {
  Backlog: 'stages.backlog',
  ToDo: 'stages.todo',
  Active: 'stages.active',
  Done: 'stages.done',
}

const API_KEYS = {
  'Assignee must be a member of the project': 'api.assigneeMustBeMember',
  'stage_id does not belong to this project': 'api.stageWrongProject',
  'The project has no Backlog stage': 'api.noWorkStage',
  'New tasks can only be created in the Backlog': 'api.backlogOnly',
  'Task not found': 'api.taskNotFound',
  'The project has no Done stage': 'api.noDoneStage',
  'WIP limits apply only to regular stages': 'api.wipRegularOnly',
  'Only regular stages can be split into sub-stages': 'api.splitRegularOnly',
  'The Backlog stage cannot be deleted': 'api.backlogUndeletable',
  'The Done stage cannot be deleted': 'api.doneUndeletable',
  'At least one work stage is required': 'api.workStageRequired',
  'stage_ids must be a permutation of the project stages': 'api.stagePermutation',
  'The Backlog stage must stay first': 'api.backlogFirst',
  'Stage not found': 'api.stageNotFound',
  'User not found': 'api.userNotFound',
  'Member not found': 'api.memberNotFound',
  'The owner cannot be removed': 'api.ownerUndeletable',
  'The owner cannot leave a project — delete it instead': 'api.ownerCannotLeave',
  'BOT_TOKEN is not configured': 'api.botToken',
  'Invalid Telegram signature': 'api.badSignature',
  'Payload contains no user data': 'api.noUserData',
  'Not found': 'api.notFound',
  'Username is required': 'api.usernameRequired',
  'Invalid refresh token': 'api.badRefresh',
  'Unknown user': 'api.unknownUser',
  'Not authenticated': 'api.notAuthenticated',
  'Invalid or expired token': 'api.badToken',
  'Project not found': 'api.projectNotFound',
  'You are not a member of this project': 'api.notMember',
  'Only the project owner can do this': 'api.ownerOnly',
}

/** Default English stage names follow the active language. Custom names stay as stored. */
export function stageName(stageOrName) {
  const name = typeof stageOrName === 'string' ? stageOrName : stageOrName?.name
  if (!name) return ''
  const key = CANONICAL_STAGES[name]
  return key ? i18n.global.t(key) : name
}

export function displayError(message) {
  if (!message) return ''
  if (i18n.global.te(message)) return i18n.global.t(message)
  const wip = /^WIP limit of (\d+) reached for stage "(.*)"$/.exec(message)
  if (wip) return i18n.global.t('errors.wipReached', { limit: wip[1], stage: stageName(wip[2]) })
  const key = API_KEYS[message]
  if (key) return i18n.global.t(key)
  return message
}
