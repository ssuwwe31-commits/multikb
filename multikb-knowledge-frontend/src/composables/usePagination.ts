import { ref, computed } from 'vue'

export const usePagination = (initialPage = 1, initialSize = 20) => {
  const page = ref(initialPage)
  const size = ref(initialSize)
  const total = ref(0)

  const totalPages = computed(() => Math.ceil(total.value / size.value))

  const hasNextPage = computed(() => page.value < totalPages.value)
  const hasPrevPage = computed(() => page.value > 1)

  const nextPage = () => {
    if (hasNextPage.value) {
      page.value++
    }
  }

  const prevPage = () => {
    if (hasPrevPage.value) {
      page.value--
    }
  }

  const setPage = (p: number) => {
    page.value = p
  }

  const setSize = (s: number) => {
    size.value = s
  }

  const setTotal = (t: number) => {
    total.value = t
  }

  const reset = () => {
    page.value = initialPage
    size.value = initialSize
    total.value = 0
  }

  return {
    page,
    size,
    total,
    totalPages,
    hasNextPage,
    hasPrevPage,
    nextPage,
    prevPage,
    setPage,
    setSize,
    setTotal,
    reset
  }
}
