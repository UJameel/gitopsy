import React from 'react';

export default function Home() {
  return (
    <div>
      <h1>Welcome to Next.js App</h1>
    </div>
  );
}

export async function getServerSideProps() {
  return { props: {} };
}
