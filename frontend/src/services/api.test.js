import test from 'node:test'
import assert from 'node:assert/strict'
import { ErrorCodes, jobService } from './api.js'

const originalFetch = globalThis.fetch
const originalLocalStorage = globalThis.localStorage
const originalFormData = globalThis.FormData

function makeResponse(body, status = 200) {
  const text = JSON.stringify(body)
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() { return body },
    async text() { return text },
  }
}

function installLocalStorage(token = null) {
  globalThis.localStorage = {
    getItem(key) {
      return key === 'winningcv_auth_token' ? token : null
    },
  }
}

test.beforeEach(() => {
  globalThis.FormData = class FormData {}
})

test.afterEach(() => {
  globalThis.fetch = originalFetch
  globalThis.localStorage = originalLocalStorage
  globalThis.FormData = originalFormData
})

test('loads one matched job from the result endpoint', async () => {
  installLocalStorage('test-token')
  let request
  globalThis.fetch = async (url, options) => {
    request = { url, options }
    return makeResponse({ id: 'recA1b2C3d4E5f6G7', job_title: 'Platform Engineer' })
  }

  const result = await jobService.getResult('recA1b2C3d4E5f6G7')

  assert.equal(result.id, 'recA1b2C3d4E5f6G7')
  assert.equal(request.url, 'http://localhost:8000/api/v1/jobs/results/recA1b2C3d4E5f6G7')
  assert.equal(request.options.credentials, 'include')
  assert.equal(request.options.headers.Authorization, 'Token test-token')
})

test('saves application tracking through the existing endpoint', async () => {
  installLocalStorage()
  let request
  globalThis.fetch = async (url, options) => {
    request = { url, options }
    return makeResponse({
      id: 'job-123',
      application_status: 'applied',
      application_notes: 'Submitted today',
    })
  }

  const result = await jobService.updateApplicationStatus('job-123', 'applied', 'Submitted today')

  assert.equal(result.application_status, 'applied')
  assert.equal(request.url, 'http://localhost:8000/api/v1/jobs/results/job-123/application')
  assert.equal(request.options.method, 'PATCH')
  assert.deepEqual(JSON.parse(request.options.body), {
    application_status: 'applied',
    application_notes: 'Submitted today',
  })
})

for (const [status, code] of [[404, ErrorCodes.NOT_FOUND], [501, ErrorCodes.SERVER_ERROR]]) {
  test(`preserves ${status} responses for workspace handling`, async () => {
    installLocalStorage()
    globalThis.fetch = async () => makeResponse({ detail: 'Unavailable' }, status)

    await assert.rejects(
      () => status === 404
        ? jobService.getResult('missing-job')
        : jobService.updateApplicationStatus('job-123', 'saved'),
      (error) => error.status === status && error.code === code,
    )
  })
}
