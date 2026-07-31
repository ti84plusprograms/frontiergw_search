export const metadata = {
  title: "Frontier GoWild Destination Explorer",
  description: "Find where you can fly today on Frontier Airlines GoWild Pass",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
