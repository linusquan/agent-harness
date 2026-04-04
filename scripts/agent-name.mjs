import { faker } from '@faker-js/faker';

const role = process.argv[2] || 'agent';
const name = faker.person.firstName().toLowerCase();
console.log(`${role}-${name}`);
