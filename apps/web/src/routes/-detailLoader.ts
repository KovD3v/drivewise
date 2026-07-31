import { notFound } from '@tanstack/react-router'

import { isApiNotFoundError } from '../api/drivewise'

export async function loadDetail<T>(load: () => Promise<T>) {
  try {
    return await load()
  } catch (error) {
    if (isApiNotFoundError(error)) {
      throw notFound()
    }
    throw error
  }
}
