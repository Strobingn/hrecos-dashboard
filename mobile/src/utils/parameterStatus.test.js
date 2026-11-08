const test = require('node:test');
const assert = require('node:assert/strict');
const { classifyParameter, getWQILevel, windowExtent } = require('./parameterStatus');

test('a score of 80 is Good, not Poor', () => {
  assert.equal(getWQILevel(80).label, 'Good');
  assert.equal(getWQILevel(80).color, getWQILevel(82).color);
  assert.equal(getWQILevel(30).label, 'Bad');
});

test('Hudson November water near 57F is normal', () => {
  assert.equal(classifyParameter('temp', 57.38).label, 'Normal');
  assert.equal(classifyParameter('temp', 58.6).label, 'Normal');
  assert.notEqual(classifyParameter('temp', 57.38).color, '#E53935');
});

test('other sonde parameters get a range instead of Unknown', () => {
  assert.equal(classifyParameter('do', 9.42).label, 'Excellent');
  assert.equal(classifyParameter('do_sat', 91.8).label, 'Excellent');
  assert.equal(classifyParameter('ph', 7.88).label, 'Optimal');
  assert.equal(classifyParameter('turbidity', 13.22).label, 'Typical');
  assert.equal(classifyParameter('turbidity', 6.8).label, 'Clear');
  assert.equal(classifyParameter('conductivity', 419.5).label, 'Fresh');
  assert.equal(classifyParameter('salinity', 0.2).label, 'Fresh');
  assert.equal(classifyParameter('salinity', 3.54).label, 'Oligohaline');
  assert.equal(classifyParameter('chlorophyll', 0.82).label, 'Low');
  assert.equal(classifyParameter('phycocyanin', 1.4).label, 'Low');
  assert.equal(classifyParameter('depth', 3.993).label, 'Typical');
  assert.equal(classifyParameter('depth', 0).label, 'Surface');
});

test('min and max include the current reading', () => {
  const extent = windowExtent(
    [{ value: 14.82 }, { value: 14.82 }],
    14.2
  );
  assert.equal(extent.min, 14.2);
  assert.equal(extent.max, 14.82);
  const turbidity = windowExtent([{ value: 14.4 }, { value: 14.4 }], 13.22);
  assert.ok(turbidity.min <= 13.22);
  assert.ok(turbidity.max >= 13.22);
});
