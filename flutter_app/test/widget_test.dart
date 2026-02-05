import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:even_g2_teleprompter/main.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(
      const ProviderScope(
        child: EvenG2App(),
      ),
    );

    // Verify that the home screen shows
    expect(find.text('Even G2 Teleprompter'), findsOneWidget);
    expect(find.text('Scan'), findsOneWidget);
  });
}
