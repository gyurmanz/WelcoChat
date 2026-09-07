// Mobile nav
const navToggle = document.getElementById('navToggle')
const navLinks = document.getElementById('navLinks')
if (navToggle && navLinks) {
  navToggle.addEventListener('click', () => navLinks.classList.toggle('open'))
  navLinks.querySelectorAll('a').forEach((a) =>
    a.addEventListener('click', () => navLinks.classList.remove('open')),
  )
}

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
  submitBtn.textContent = 'Sending...'

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
    if (!res.ok) throw new Error(data.detail || 'Something went wrong. Please try again.')
    msg.textContent = 'Thank you. We received your message and will get back to you soon.'
    msg.className = 'form-msg ok'
    form.reset()
  } catch (err) {
    msg.textContent = err instanceof Error ? err.message : 'Something went wrong. Please try again.'
    msg.className = 'form-msg err'
  } finally {
    submitBtn.disabled = false
    submitBtn.textContent = original
  }
})
}
