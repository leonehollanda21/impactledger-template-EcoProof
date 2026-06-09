<template>
  <footer class="app-footer">
    <div class="container footer-content">
      <p class="muted">
        © 2026 EcoProof — Todas as ações comprovadas em blockchain. 🌿
      </p>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  background-color: #f9fafb;
  border-top: 1px solid var(--color-border, #e2e8f0);
  padding: 1.5rem 0;
  margin-top: auto; 
  text-align: center;
  width: 100%;
}

.footer-content {
  display: flex;
  justify-content: center;
  align-items: center;
}

.muted {
  color: var(--color-muted, #64748b);
  font-size: 0.9rem;
  font-weight: 500;
  margin: 0;
}
</style>