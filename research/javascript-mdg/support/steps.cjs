'use strict';

const assert = require('node:assert/strict');
const { Given, When, Then } = require('@cucumber/cucumber');
const { add } = require('../src/math.cjs');

Given('the numbers {int} and {int}', function (left, right) {
  this.left = left;
  this.right = right;
});

When('they are added', function () {
  this.result = add(this.left, this.right);
});

Then('the result is {int}', function (expected) {
  assert.equal(this.result, expected);
});
