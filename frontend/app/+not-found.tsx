import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { Colors, Fonts, Type, Space } from '../constants/theme';
import { AnchorIcon } from '../components/icons';

export default function NotFoundScreen() {
  const router = useRouter();
  return (
    <View style={styles.container}>
      <AnchorIcon size={36} color={Colors.text3} />
      <Text style={styles.title}>Page not found</Text>
      <Pressable onPress={() => router.replace('/')} style={styles.btn}>
        <Text style={styles.btnText}>Go back</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.bg1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Space.lg,
  },
  title: {
    fontFamily: Fonts.body,
    fontSize: Type.lg.fontSize,
    color: Colors.text2,
  },
  btn: {
    backgroundColor: Colors.bg3,
    paddingHorizontal: Space.xl,
    paddingVertical: Space.md,
    borderRadius: 10,
  },
  btnText: {
    fontFamily: Fonts.bodySemibold,
    fontSize: Type.sm.fontSize,
    color: Colors.text1,
  },
});
