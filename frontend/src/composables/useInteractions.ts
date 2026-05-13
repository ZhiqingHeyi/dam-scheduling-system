/**
 * 智能仓面排序系统 - 交互效果组合式函数
 * 提供鼠标跟随光晕、悬停效果等交互逻辑
 */
import { ref, onMounted, onUnmounted, type Ref } from 'vue'

// ============================================
// 类型定义
// ============================================

interface CursorPosition {
  x: number
  y: number
}

interface InteractionOptions {
  enableCursorGlow?: boolean
  enableTiltEffect?: boolean
  enableMagneticEffect?: boolean
  glowSize?: number
  glowColor?: string
}

// ============================================
// 1. 鼠标跟随光晕效果
// ============================================

export function useCursorGlow(
  elementRef: Ref<HTMLElement | null>,
  options: { glowSize?: number; glowColor?: string } = {}
) {
  const { glowSize = 300, glowColor = 'rgba(0, 240, 255, 0.08)' } = options
  const isHovering = ref(false)
  const cursorPosition = ref<CursorPosition>({ x: 0, y: 0 })
  let rafId: number | null = null
  let targetX = 0
  let targetY = 0
  let currentX = 0
  let currentY = 0
  let element: HTMLElement | null = null

  const handleMouseMove = (e: MouseEvent) => {
    if (!element) return
    
    const rect = element.getBoundingClientRect()
    targetX = e.clientX - rect.left
    targetY = e.clientY - rect.top
  }

  const handleMouseEnter = () => {
    isHovering.value = true
    startAnimation()
  }

  const handleMouseLeave = () => {
    isHovering.value = false
    stopAnimation()
  }

  const animate = () => {
    // 平滑插值
    const ease = 0.15
    currentX += (targetX - currentX) * ease
    currentY += (targetY - currentY) * ease

    cursorPosition.value = { x: currentX, y: currentY }

    if (element) {
      element.style.setProperty('--cursor-x', `${currentX}px`)
      element.style.setProperty('--cursor-y', `${currentY}px`)
    }

    rafId = requestAnimationFrame(animate)
  }

  const startAnimation = () => {
    if (!rafId) {
      rafId = requestAnimationFrame(animate)
    }
  }

  const stopAnimation = () => {
    if (rafId) {
      cancelAnimationFrame(rafId)
      rafId = null
    }
  }

  onMounted(() => {
    element = elementRef.value
    if (!element) return

    element.addEventListener('mousemove', handleMouseMove, { passive: true })
    element.addEventListener('mouseenter', handleMouseEnter)
    element.addEventListener('mouseleave', handleMouseLeave)
  })

  onUnmounted(() => {
    stopAnimation()
    if (element) {
      element.removeEventListener('mousemove', handleMouseMove)
      element.removeEventListener('mouseenter', handleMouseEnter)
      element.removeEventListener('mouseleave', handleMouseLeave)
      element = null
    }
  })

  return {
    isHovering,
    cursorPosition
  }
}

// ============================================
// 2. 3D 倾斜效果
// ============================================

export function useTiltEffect(
  elementRef: Ref<HTMLElement | null>,
  options: { maxTilt?: number; perspective?: number; scale?: number } = {}
) {
  const { maxTilt = 5, perspective = 1000, scale = 1.02 } = options
  const isHovering = ref(false)
  const transform = ref('')
  let element: HTMLElement | null = null

  const handleMouseMove = (e: MouseEvent) => {
    if (!element) return

    const rect = element.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const centerX = rect.width / 2
    const centerY = rect.height / 2

    const rotateX = ((y - centerY) / centerY) * -maxTilt
    const rotateY = ((x - centerX) / centerX) * maxTilt

    transform.value = `perspective(${perspective}px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(${scale}, ${scale}, ${scale})`
    element.style.transform = transform.value
  }

  const handleMouseEnter = () => {
    isHovering.value = true
  }

  const handleMouseLeave = () => {
    isHovering.value = false
    transform.value = `perspective(${perspective}px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`
    if (element) {
      element.style.transform = transform.value
    }
  }

  onMounted(() => {
    element = elementRef.value
    if (!element) return

    element.style.transition = 'transform 0.1s ease-out'
    element.addEventListener('mousemove', handleMouseMove, { passive: true })
    element.addEventListener('mouseenter', handleMouseEnter)
    element.addEventListener('mouseleave', handleMouseLeave)
  })

  onUnmounted(() => {
    if (element) {
      element.removeEventListener('mousemove', handleMouseMove)
      element.removeEventListener('mouseenter', handleMouseEnter)
      element.removeEventListener('mouseleave', handleMouseLeave)
      element = null
    }
  })

  return {
    isHovering,
    transform
  }
}

// ============================================
// 3. 磁性吸附效果
// ============================================

export function useMagneticEffect(
  elementRef: Ref<HTMLElement | null>,
  options: { strength?: number; radius?: number } = {}
) {
  const { strength = 0.3, radius = 100 } = options
  const isHovering = ref(false)
  let element: HTMLElement | null = null

  const handleMouseMove = (e: MouseEvent) => {
    if (!element) return

    const rect = element.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2

    const distanceX = e.clientX - centerX
    const distanceY = e.clientY - centerY
    const distance = Math.sqrt(distanceX * distanceX + distanceY * distanceY)

    if (distance < radius) {
      isHovering.value = true
      const factor = (1 - distance / radius) * strength
      const moveX = distanceX * factor
      const moveY = distanceY * factor

      element.style.transform = `translate(${moveX}px, ${moveY}px)`
    } else {
      isHovering.value = false
      element.style.transform = 'translate(0, 0)'
    }
  }

  const handleMouseLeave = () => {
    isHovering.value = false
    if (element) {
      element.style.transform = 'translate(0, 0)'
    }
  }

  onMounted(() => {
    element = elementRef.value
    if (!element) return

    element.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
    document.addEventListener('mousemove', handleMouseMove, { passive: true })
    element.addEventListener('mouseleave', handleMouseLeave)
  })

  onUnmounted(() => {
    document.removeEventListener('mousemove', handleMouseMove)
    if (element) {
      element.removeEventListener('mouseleave', handleMouseLeave)
      element = null
    }
  })

  return {
    isHovering
  }
}

// ============================================
// 4. 数据更新闪烁效果
// ============================================

export function useDataFlash(elementRef: Ref<HTMLElement | null>) {
  let element: HTMLElement | null = null

  const flash = () => {
    if (!element) return

    element.classList.add('data-flash')
    
    setTimeout(() => {
      element?.classList.remove('data-flash')
    }, 800)
  }

  onMounted(() => {
    element = elementRef.value
  })

  onUnmounted(() => {
    element = null
  })

  return {
    flash
  }
}

// ============================================
// 5. 滚动触发动画
// ============================================

export function useScrollReveal(
  elementRef: Ref<HTMLElement | null>,
  options: { threshold?: number; rootMargin?: string } = {}
) {
  const { threshold = 0.1, rootMargin = '0px' } = options
  const isVisible = ref(false)
  let observer: IntersectionObserver | null = null
  let element: HTMLElement | null = null

  onMounted(() => {
    element = elementRef.value
    if (!element) return

    observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            isVisible.value = true
            observer?.unobserve(entry.target)
          }
        })
      },
      { threshold, rootMargin }
    )

    observer.observe(element)
  })

  onUnmounted(() => {
    if (observer && element) {
      observer.unobserve(element)
    }
    element = null
  })

  return {
    isVisible
  }
}

// ============================================
// 6. 组合式交互 Hook
// ============================================

export function useInteractions(
  elementRef: Ref<HTMLElement | null>,
  options: InteractionOptions = {}
) {
  const {
    enableCursorGlow = true,
    enableTiltEffect = false,
    enableMagneticEffect = false
  } = options

  const interactions: Record<string, any> = {}

  if (enableCursorGlow) {
    interactions.cursorGlow = useCursorGlow(elementRef)
  }

  if (enableTiltEffect) {
    interactions.tilt = useTiltEffect(elementRef)
  }

  if (enableMagneticEffect) {
    interactions.magnetic = useMagneticEffect(elementRef)
  }

  return interactions
}

// ============================================
// 7. 性能优化工具
// ============================================

/**
 * 节流函数
 */
export function throttle<T extends (...args: any[]) => void>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false
  return function (this: any, ...args: Parameters<T>) {
    if (!inThrottle) {
      func.apply(this, args)
      inThrottle = true
      setTimeout(() => (inThrottle = false), limit)
    }
  }
}

/**
 * 防抖函数
 */
export function debounce<T extends (...args: any[]) => void>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null
  return function (this: any, ...args: Parameters<T>) {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => func.apply(this, args), wait)
  }
}

// ============================================
// 8. 全局交互管理
// ============================================

export function useGlobalInteractions() {
  const isTouchDevice = ref(false)
  const prefersReducedMotion = ref(false)

  onMounted(() => {
    // 检测触摸设备
    isTouchDevice.value = window.matchMedia('(hover: none) and (pointer: coarse)').matches
    
    // 检测减少动画偏好
    prefersReducedMotion.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    // 添加全局类
    if (isTouchDevice.value) {
      document.body.classList.add('touch-device')
    }
    
    if (prefersReducedMotion.value) {
      document.body.classList.add('reduced-motion')
    }
  })

  return {
    isTouchDevice,
    prefersReducedMotion
  }
}
