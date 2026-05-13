<template>
  <div class="app-container">
    <header class="glass-header">
      <div class="header-inner">
        <!-- 左侧：装饰线条 + 公司标识 -->
        <div class="header-left">
          <div class="deco-line left-line">
            <div class="deco-glow"></div>
            <div class="extra-dots"></div>
          </div>
          <div class="company-badge">
            <span class="badge-icon"></span>
            <span class="badge-text">葛洲坝第二工程有限公司研发</span>
            <span class="badge-glow"></span>
          </div>
        </div>
        
        <!-- 中间：主标题 -->
        <div class="header-center">
          <div class="title-decoration left">
            <span class="deco-square"></span>
            <span class="deco-line-h"></span>
          </div>
          <h1 class="main-title">
            <span class="title-text">QBT水利枢纽工程智能排仓系统</span>
            <span class="title-scan"></span>
          </h1>
          <div class="title-decoration right">
            <span class="deco-line-h"></span>
            <span class="deco-square"></span>
          </div>
          <div class="title-glow"></div>
          <div class="title-bottom-line"></div>
        </div>
        
        <!-- 右侧：装饰线条 -->
        <div class="header-right">
          <div class="deco-line right-line">
            <div class="deco-glow"></div>
            <div class="extra-dots"></div>
          </div>
        </div>
      </div>
    </header>
    
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="glass-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    
    <footer class="glass-footer">
      <p>© 2026 智能建造实验室 · 拱坝施工智能调度平台 · 葛洲坝第二工程有限公司研发</p>
      <div class="footer-line"></div>
    </footer>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped lang="scss">
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.glass-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: linear-gradient(
    180deg,
    rgba(2, 6, 23, 0.98) 0%,
    rgba(5, 16, 37, 0.95) 100%
  );
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(0, 200, 255, 0.3);
  
  // 顶部发光边框
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg,
      transparent 0%,
      rgba(0, 200, 255, 0.8) 20%,
      rgba(0, 240, 255, 1) 50%,
      rgba(0, 200, 255, 0.8) 80%,
      transparent 100%
    );
  }
  
  .header-inner {
    max-width: 1920px;
    margin: 0 auto;
    padding: 12px 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: relative;
  }
}

// 左侧区域
.header-left {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 8px;
  flex: 1;
  position: relative;
  padding-left: 10px;

  .deco-line {
    position: relative;
    width: 320px;
    height: 2px;
    background: linear-gradient(90deg,
      rgba(0, 200, 255, 0.95) 0%,
      rgba(0, 200, 255, 0.6) 30%,
      rgba(0, 200, 255, 0.2) 70%,
      transparent 100%
    );
    animation: linePulse 2s ease-in-out infinite;
    
    // 主发光点
    &::before {
      content: '';
      position: absolute;
      top: 50%;
      left: 0;
      transform: translateY(-50%);
      width: 8px;
      height: 8px;
      background: radial-gradient(circle, rgba(0, 240, 255, 1), rgba(0, 200, 255, 0.5));
      border-radius: 50%;
      box-shadow: 0 0 10px rgba(0, 240, 255, 0.8), 0 0 20px rgba(0, 200, 255, 0.5);
      animation: dotPulse 2s ease-in-out infinite;
    }
    
    // 折线装饰
    &::after {
      content: '';
      position: absolute;
      top: -6px;
      left: 20px;
      width: 40px;
      height: 14px;
      border: 2px solid rgba(0, 200, 255, 0.6);
      border-left: none;
      border-bottom: none;
      transform: skewX(-30deg);
      animation: cornerPulse 2s ease-in-out infinite;
    }
    
    .deco-glow {
      position: absolute;
      top: 50%;
      left: 0;
      transform: translateY(-50%);
      width: 150px;
      height: 20px;
      background: radial-gradient(ellipse 100% 50% at left center, rgba(0, 240, 255, 0.4), transparent);
      filter: blur(8px);
      animation: glowPulse 2s ease-in-out infinite;
    }
    
    // 额外装饰点
    .extra-dots {
      position: absolute;
      top: 50%;
      left: 60px;
      transform: translateY(-50%);
      display: flex;
      gap: 8px;
      
      &::before,
      &::after {
        content: '';
        width: 4px;
        height: 4px;
        background: rgba(0, 200, 255, 0.8);
        border-radius: 50%;
        box-shadow: 0 0 6px rgba(0, 200, 255, 0.6);
      }
    }
  }
  
  // 公司标识徽章
  .company-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 12px;
    background: linear-gradient(
      135deg,
      rgba(0, 150, 255, 0.15) 0%,
      rgba(0, 100, 200, 0.1) 50%,
      rgba(0, 150, 255, 0.15) 100%
    );
    border: 1px solid rgba(0, 200, 255, 0.25);
    border-radius: 4px;
    position: relative;
    overflow: hidden;
    backdrop-filter: blur(4px);
    margin-top: 4px;
    margin-left: 20px;

    // 左侧发光边角
    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 8px;
      height: 8px;
      border-top: 2px solid rgba(0, 240, 255, 0.8);
      border-left: 2px solid rgba(0, 240, 255, 0.8);
    }

    // 右侧发光边角
    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      right: 0;
      width: 8px;
      height: 8px;
      border-bottom: 2px solid rgba(0, 240, 255, 0.8);
      border-right: 2px solid rgba(0, 240, 255, 0.8);
    }

    .badge-icon {
      width: 6px;
      height: 6px;
      background: radial-gradient(circle, rgba(0, 240, 255, 1), rgba(0, 200, 255, 0.6));
      border-radius: 50%;
      box-shadow: 0 0 8px rgba(0, 240, 255, 0.8), 0 0 16px rgba(0, 200, 255, 0.4);
      animation: badgePulse 2s ease-in-out infinite;
    }

    .badge-text {
      font-size: 11px;
      color: rgba(180, 220, 255, 0.9);
      letter-spacing: 2px;
      font-weight: 500;
      text-shadow: 0 0 10px rgba(0, 200, 255, 0.3);
      white-space: nowrap;
    }

    .badge-glow {
      position: absolute;
      top: 0;
      left: -100%;
      width: 50%;
      height: 100%;
      background: linear-gradient(
        90deg,
        transparent,
        rgba(255, 255, 255, 0.15),
        transparent
      );
      animation: badgeShine 3s ease-in-out infinite;
    }

    &:hover {
      border-color: rgba(0, 240, 255, 0.4);
      background: linear-gradient(
        135deg,
        rgba(0, 150, 255, 0.2) 0%,
        rgba(0, 100, 200, 0.15) 50%,
        rgba(0, 150, 255, 0.2) 100%
      );

      .badge-text {
        color: rgba(200, 240, 255, 1);
        text-shadow: 0 0 12px rgba(0, 240, 255, 0.5);
      }
    }
  }
}

// 中间标题区域
.header-center {
  position: relative;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  padding: 0 20px;
  gap: 16px;
  
  // 标题装饰
  .title-decoration {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .deco-square {
      width: 8px;
      height: 8px;
      background: linear-gradient(135deg, rgba(0, 240, 255, 1), rgba(0, 200, 255, 0.6));
      transform: rotate(45deg);
      box-shadow: 0 0 10px rgba(0, 240, 255, 0.8);
      animation: squarePulse 2s ease-in-out infinite;
    }
    
    .deco-line-h {
      width: 30px;
      height: 2px;
      background: linear-gradient(90deg, rgba(0, 200, 255, 0.8), rgba(0, 240, 255, 0.4));
      animation: linePulse 2s ease-in-out infinite;
    }
    
    &.right {
      .deco-line-h {
        background: linear-gradient(90deg, rgba(0, 240, 255, 0.4), rgba(0, 200, 255, 0.8));
      }
    }
  }
  
  .main-title {
    position: relative;
    font-size: 26px;
    font-weight: 700;
    color: #fff;
    margin: 0;
    letter-spacing: 4px;
    white-space: nowrap;
    
    .title-text {
      display: inline-block;
      text-shadow: 
        0 0 10px rgba(0, 200, 255, 0.8),
        0 0 30px rgba(0, 200, 255, 0.5),
        0 0 50px rgba(0, 200, 255, 0.3),
        0 0 80px rgba(0, 150, 255, 0.2);
      background: linear-gradient(
        180deg,
        #ffffff 0%,
        #e0f4ff 30%,
        #a0e0ff 60%,
        #70d0ff 100%
      );
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      animation: titleShine 3s ease-in-out infinite;
    }
    
    // 扫描线效果 - 带渐进消失
    .title-scan {
      position: absolute;
      top: 0;
      left: -50%;
      width: 40%;
      height: 100%;
      background: linear-gradient(
        90deg,
        transparent 0%,
        rgba(255, 255, 255, 0.1) 20%,
        rgba(255, 255, 255, 0.5) 50%,
        rgba(255, 255, 255, 0.1) 80%,
        transparent 100%
      );
      filter: blur(2px);
      animation: scanMove 3s ease-out infinite;
      pointer-events: none;
      opacity: 0;
    }
  }
  
  .title-glow {
    position: absolute;
    bottom: -15px;
    left: 50%;
    transform: translateX(-50%);
    width: 100%;
    height: 30px;
    background: radial-gradient(ellipse 80% 50% at center, rgba(0, 200, 255, 0.5), transparent 70%);
    filter: blur(12px);
    animation: glowPulse 2s ease-in-out infinite;
  }
  
  // 底部装饰线
  .title-bottom-line {
    position: absolute;
    bottom: -8px;
    left: 50%;
    transform: translateX(-50%);
    width: 60%;
    height: 2px;
    background: linear-gradient(90deg,
      transparent 0%,
      rgba(0, 200, 255, 0.6) 20%,
      rgba(0, 240, 255, 0.9) 50%,
      rgba(0, 200, 255, 0.6) 80%,
      transparent 100%
    );
    box-shadow: 0 0 10px rgba(0, 200, 255, 0.5);
    animation: bottomLinePulse 2s ease-in-out infinite;
    
    // 流光效果
    &::after {
      content: '';
      position: absolute;
      top: 0;
      left: -100%;
      width: 50%;
      height: 100%;
      background: linear-gradient(90deg,
        transparent,
        rgba(255, 255, 255, 0.8),
        transparent
      );
      animation: lineFlow 3s linear infinite;
    }
  }
}

// 右侧区域
.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
  flex: 1;
  justify-content: flex-end;

  .deco-line {
    position: relative;
    width: 320px;
    height: 2px;
    background: linear-gradient(90deg,
      transparent 0%,
      rgba(0, 200, 255, 0.2) 30%,
      rgba(0, 200, 255, 0.6) 70%,
      rgba(0, 200, 255, 0.95) 100%
    );
    animation: linePulse 2s ease-in-out infinite;
    
    // 主发光点
    &::before {
      content: '';
      position: absolute;
      top: 50%;
      right: 0;
      transform: translateY(-50%);
      width: 8px;
      height: 8px;
      background: radial-gradient(circle, rgba(0, 240, 255, 1), rgba(0, 200, 255, 0.5));
      border-radius: 50%;
      box-shadow: 0 0 10px rgba(0, 240, 255, 0.8), 0 0 20px rgba(0, 200, 255, 0.5);
      animation: dotPulse 2s ease-in-out infinite;
    }
    
    // 折线装饰
    &::after {
      content: '';
      position: absolute;
      top: -6px;
      right: 20px;
      width: 40px;
      height: 14px;
      border: 2px solid rgba(0, 200, 255, 0.6);
      border-right: none;
      border-bottom: none;
      transform: skewX(30deg);
      animation: cornerPulse 2s ease-in-out infinite;
    }
    
    .deco-glow {
      position: absolute;
      top: 50%;
      right: 0;
      transform: translateY(-50%);
      width: 150px;
      height: 20px;
      background: radial-gradient(ellipse 100% 50% at right center, rgba(0, 240, 255, 0.4), transparent);
      filter: blur(8px);
      animation: glowPulse 2s ease-in-out infinite;
    }
    
    // 额外装饰点
    .extra-dots {
      position: absolute;
      top: 50%;
      right: 60px;
      transform: translateY(-50%);
      display: flex;
      gap: 8px;
      
      &::before,
      &::after {
        content: '';
        width: 4px;
        height: 4px;
        background: rgba(0, 200, 255, 0.8);
        border-radius: 50%;
        box-shadow: 0 0 6px rgba(0, 200, 255, 0.6);
      }
    }
  }
}

// 动画定义
@keyframes linePulse {
  0%, 100% {
    opacity: 0.6;
    box-shadow: 0 0 5px rgba(0, 200, 255, 0.3);
  }
  50% {
    opacity: 1;
    box-shadow: 0 0 15px rgba(0, 200, 255, 0.8), 0 0 30px rgba(0, 240, 255, 0.4);
  }
}

@keyframes arrowPulse {
  0%, 100% {
    opacity: 0.7;
    transform: scaleX(1);
    filter: brightness(1);
  }
  50% {
    opacity: 1;
    transform: scaleX(1.1);
    filter: brightness(1.3);
  }
}

@keyframes smallArrowPulse {
  0%, 100% {
    opacity: 0.5;
    transform: scaleX(1);
  }
  50% {
    opacity: 0.9;
    transform: scaleX(1.15);
  }
}

@keyframes glowPulse {
  0%, 100% {
    opacity: 0.4;
    transform: scaleX(1);
    filter: blur(4px);
  }
  50% {
    opacity: 0.9;
    transform: scaleX(1.3);
    filter: blur(6px);
  }
}

// 徽章动画
@keyframes badgePulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 8px rgba(0, 240, 255, 0.8), 0 0 16px rgba(0, 200, 255, 0.4);
  }
  50% {
    transform: scale(1.2);
    box-shadow: 0 0 12px rgba(0, 240, 255, 1), 0 0 24px rgba(0, 200, 255, 0.6);
  }
}

@keyframes badgeShine {
  0% {
    left: -100%;
  }
  50%, 100% {
    left: 150%;
  }
}

// 圆点脉冲动画
@keyframes dotPulse {
  0%, 100% {
    transform: translateY(-50%) scale(1);
    box-shadow: 0 0 10px rgba(0, 240, 255, 0.8), 0 0 20px rgba(0, 200, 255, 0.5);
  }
  50% {
    transform: translateY(-50%) scale(1.3);
    box-shadow: 0 0 15px rgba(0, 240, 255, 1), 0 0 30px rgba(0, 200, 255, 0.8);
  }
}

// 折线闪烁动画
@keyframes cornerPulse {
  0%, 100% {
    opacity: 0.6;
    border-color: rgba(0, 200, 255, 0.6);
  }
  50% {
    opacity: 1;
    border-color: rgba(0, 240, 255, 0.9);
  }
}

// 标题相关动画
@keyframes squarePulse {
  0%, 100% {
    transform: rotate(45deg) scale(1);
    box-shadow: 0 0 10px rgba(0, 240, 255, 0.8);
  }
  50% {
    transform: rotate(45deg) scale(1.2);
    box-shadow: 0 0 15px rgba(0, 240, 255, 1), 0 0 25px rgba(0, 200, 255, 0.6);
  }
}

@keyframes titleShine {
  0%, 100% {
    filter: brightness(1);
  }
  50% {
    filter: brightness(1.2);
  }
}

@keyframes scanMove {
  0% {
    left: -50%;
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  70% {
    left: 110%;
    opacity: 1;
  }
  90%, 100% {
    left: 120%;
    opacity: 0;
  }
}

@keyframes bottomLinePulse {
  0%, 100% {
    opacity: 0.6;
    box-shadow: 0 0 10px rgba(0, 200, 255, 0.5);
  }
  50% {
    opacity: 1;
    box-shadow: 0 0 20px rgba(0, 240, 255, 0.8), 0 0 30px rgba(0, 200, 255, 0.5);
  }
}

@keyframes lineFlow {
  0% {
    left: -100%;
  }
  100% {
    left: 200%;
  }
}

// 响应式适配
@media (max-width: 1600px) {
  .glass-header {
    .header-inner {
      padding: 12px 30px;
    }
  }

  .header-left,
  .header-right {
    .deco-line {
      width: 250px;
    }
  }

  .header-left {
    .company-badge {
      padding: 3px 10px;
      margin-left: 15px;

      .badge-text {
        font-size: 10px;
        letter-spacing: 1.5px;
      }
    }
  }

  .header-center {
    .main-title {
      font-size: 22px;
      letter-spacing: 2px;
    }
  }
}

@media (max-width: 1200px) {
  .glass-header {
    .header-inner {
      padding: 10px 20px;
    }
  }

  .header-left,
  .header-right {
    .deco-line {
      width: 100px;

      &::before,
      &::after {
        display: none;
      }
    }
  }

  .header-left {
    padding-left: 5px;

    .company-badge {
      padding: 2px 8px;
      margin-left: 10px;

      .badge-text {
        font-size: 9px;
        letter-spacing: 1px;
      }

      .badge-icon {
        width: 5px;
        height: 5px;
      }
    }
  }

  .header-center {
    padding: 0 20px;

    .main-title {
      font-size: 18px;
      letter-spacing: 1px;
    }
  }
}

@media (max-width: 900px) {
  .header-left,
  .header-right {
    .deco-line {
      display: none;
    }
  }

  .header-left {
    .company-badge {
      padding: 2px 6px;
      margin-left: 5px;

      .badge-text {
        font-size: 8px;
        letter-spacing: 0.5px;
      }

      .badge-icon {
        width: 4px;
        height: 4px;
      }

      &::before,
      &::after {
        width: 6px;
        height: 6px;
        border-width: 1px;
      }
    }
  }

  .header-center {
    .main-title {
      font-size: 16px;
      letter-spacing: 0;
    }
  }
}

@media (max-width: 600px) {
  .glass-header {
    .header-inner {
      padding: 10px 15px;
    }
  }

  .header-left {
    .company-badge {
      display: none;
    }
  }

  .header-center {
    .main-title {
      font-size: 14px;
    }
  }
}

.app-main {
  flex: 1;
  max-width: 1920px;
  width: 100%;
  margin: 0 auto;
  padding: 24px 28px;
}

.glass-footer {
  text-align: center;
  padding: 18px;
  position: relative;
  
  p {
    margin: 0;
    color: var(--text-muted);
    font-size: 12px;
    letter-spacing: 0.5px;
  }
  
  .footer-line {
    position: absolute;
    top: 0;
    left: 15%;
    right: 15%;
    height: 1px;
    background: linear-gradient(90deg,
      transparent,
      rgba(0, 200, 255, 0.25),
      transparent
    );
  }
}

.glass-fade-enter-active,
.glass-fade-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-fade-enter-from {
  opacity: 0;
  transform: translateY(15px) scale(0.98);
  filter: blur(4px);
}

.glass-fade-leave-to {
  opacity: 0;
  transform: translateY(-15px) scale(0.98);
  filter: blur(4px);
}
</style>
