// Mobile nav
const navToggle = document.getElementById('navToggle')
const navLinks = document.getElementById('navLinks')
if (navToggle && navLinks) {
  navToggle.addEventListener('click', () => navLinks.classList.toggle('open'))
  navLinks.querySelectorAll('a').forEach((a) =>
    a.addEventListener('click', () => navLinks.classList.remove('open')),
  )
}

// Language switcher dropdown
document.querySelectorAll('[data-lang-switch]').forEach((el) => {
  const btn = el.querySelector('.lang-switch-btn')
  if (!btn) return
  const close = () => {
    el.classList.remove('open')
    btn.setAttribute('aria-expanded', 'false')
  }
  btn.addEventListener('click', (e) => {
    e.stopPropagation()
    const isOpen = el.classList.toggle('open')
    btn.setAttribute('aria-expanded', String(isOpen))
  })
  document.addEventListener('click', (e) => {
    if (!el.contains(e.target)) close()
  })
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') close()
  })
})

// Billing toggle (monthly / annual)
const pricingSection = document.getElementById('pricing')
document.querySelectorAll('.billing-opt').forEach((btn) => {
  btn.addEventListener('click', () => {
    const mode = btn.dataset.billing
    document.querySelectorAll('.billing-opt').forEach((b) => b.classList.toggle('active', b === btn))
    if (pricingSection) pricingSection.classList.toggle('annual', mode === 'annual')
  })
})

// FAQ accordion
document.querySelectorAll('.faq-q').forEach((q) => {
  q.addEventListener('click', () => q.parentElement.classList.toggle('open'))
})

// Contact form
const form = document.getElementById('contactForm')
const msg = document.getElementById('formMsg')
const submitBtn = document.getElementById('contactSubmit')

if (form) {
form.addEventListener('submit', async (e) => {
  e.preventDefault()
  msg.textContent = ''
  msg.className = 'form-msg'
  submitBtn.disabled = true
  const original = submitBtn.textContent
  const sendingLabel = submitBtn.dataset.sendingLabel || 'Sending...'
  const successLabel = submitBtn.dataset.successLabel || 'Thank you. We received your message and will get back to you soon.'
  const errorLabel = submitBtn.dataset.errorLabel || 'Something went wrong. Please try again.'
  submitBtn.textContent = sendingLabel

  const payload = {
    name: form.name.value.trim(),
    company: form.company.value.trim(),
    email: form.email.value.trim(),
    website: form.website.value.trim(),
    topic: form.topic.value,
    message: form.message.value.trim(),
  }

  try {
    const res = await fetch('/api/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || errorLabel)
    msg.textContent = successLabel
    msg.className = 'form-msg ok'
    form.reset()
  } catch (err) {
    msg.textContent = err instanceof Error ? err.message : errorLabel
    msg.className = 'form-msg err'
  } finally {
    submitBtn.disabled = false
    submitBtn.textContent = original
  }
})
}

// Language switcher persistence (root redirector reads this on next visit)
try {
  var htmlLang = document.documentElement.getAttribute('lang')
  if (htmlLang) localStorage.setItem('welco_lang', htmlLang)
} catch (e) {}
