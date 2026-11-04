// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest'
import { clearToken, getToken, setToken } from './api'

describe('API token storage', () => {
  beforeEach(() => localStorage.clear())

  it('stores and clears the access token', () => {
    setToken('test-token')
    expect(getToken()).toBe('test-token')
    clearToken()
    expect(getToken()).toBeNull()
  })
})
